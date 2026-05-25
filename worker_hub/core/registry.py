"""Registry de workers + health checks periódicos.

Carga `workers.json` al arrancar, descubre los modelos de cada worker via
`GET /v1/models`, y refresca cada `HEALTH_CHECK_INTERVAL` segundos.

Estado en RAM (no se persiste): `{name: WorkerState}`.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from dataclasses import dataclass, field
from pathlib import Path

import httpx

log = logging.getLogger("worker_hub.registry")

HEALTH_CHECK_INTERVAL = int(os.getenv("WORKER_HUB_HEALTH_INTERVAL", "30"))
HEALTH_CHECK_TIMEOUT  = int(os.getenv("WORKER_HUB_HEALTH_TIMEOUT", "5"))


@dataclass
class WorkerState:
    name: str
    base_url: str
    priority: int
    enabled: bool
    api_key_env: str | None
    notes: str = ""

    # Mutables
    models: set[str] = field(default_factory=set)
    healthy: bool = False
    last_check: float = 0.0
    last_error: str = ""

    @property
    def api_key(self) -> str | None:
        if not self.api_key_env:
            return None
        v = os.getenv(self.api_key_env, "").strip()
        return v or None


class Registry:
    """Pool de workers ordenado por prioridad descendente."""

    def __init__(self, config_path: Path) -> None:
        self.config_path = config_path
        self.workers: dict[str, WorkerState] = {}
        self._task: asyncio.Task | None = None
        self._client: httpx.AsyncClient | None = None
        self._load()

    def _load(self) -> None:
        with open(self.config_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        for w in cfg.get("workers", []):
            name = w["name"]
            self.workers[name] = WorkerState(
                name=name,
                base_url=w["base_url"].rstrip("/"),
                priority=w.get("priority", 0),
                enabled=w.get("enabled", True),
                api_key_env=w.get("api_key_env"),
                notes=w.get("notes", ""),
            )
        log.info(f"registry cargado: {len(self.workers)} workers ({list(self.workers)})")

    async def start(self) -> None:
        """Arranca el loop de health checks."""
        self._client = httpx.AsyncClient(timeout=HEALTH_CHECK_TIMEOUT)
        # Probe inicial sincrónico (bloquea el startup hasta tener un mapa de modelos)
        await self._probe_all()
        self._task = asyncio.create_task(self._loop(), name="worker_hub_health")

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        if self._client:
            await self._client.aclose()

    async def _loop(self) -> None:
        while True:
            try:
                await asyncio.sleep(HEALTH_CHECK_INTERVAL)
                await self._probe_all()
            except asyncio.CancelledError:
                raise
            except Exception as e:
                log.warning(f"health loop error: {e}")

    async def _probe_all(self) -> None:
        """Probe paralelo a todos los workers habilitados."""
        await asyncio.gather(
            *(self._probe_one(w) for w in self.workers.values() if w.enabled),
            return_exceptions=True,
        )

    async def _probe_one(self, w: WorkerState) -> None:
        """Probe /v1/models. Tolerante: si el server responde 200 pero no devuelve
        JSON con catálogo (caso reverse-proxy que solo expone POST), el worker
        sigue healthy con `models=set()`. Solo se marca UNHEALTHY si el server no
        responde o devuelve error HTTP.
        """
        url = f"{w.base_url}/models"
        headers = {}
        if w.api_key:
            headers["Authorization"] = f"Bearer {w.api_key}"
        try:
            r = await self._client.get(url, headers=headers)
            r.raise_for_status()
        except Exception as e:
            if w.healthy:
                log.warning(f"worker '{w.name}' marcado UNHEALTHY: {e}")
            w.healthy = False
            w.last_error = str(e)[:200]
            w.last_check = time.time()
            return

        # Hasta aquí: HTTP 2xx. El server está vivo → healthy aunque no tenga catálogo.
        new_models: set[str] = set()
        try:
            data = r.json()
            if isinstance(data, dict):
                new_models = {m["id"] for m in data.get("data", []) if isinstance(m, dict) and "id" in m}
        except Exception:
            # Body no es JSON (HTML, texto, etc.). Worker vivo, catálogo ausente.
            pass

        if new_models != w.models:
            added = new_models - w.models
            removed = w.models - new_models
            msg = []
            if added:   msg.append(f"+{sorted(added)}")
            if removed: msg.append(f"-{sorted(removed)}")
            log.info(f"worker '{w.name}' models cambiaron: {' '.join(msg)}")
        w.models = new_models
        if not w.healthy:
            log.info(f"worker '{w.name}' recuperado (healthy)")
        w.healthy = True
        w.last_error = "" if new_models else "responde 200 pero /models no devuelve catalogo"
        w.last_check = time.time()

    # ──────────────────────────────────────────────────────────────────
    # Selección de worker
    # ──────────────────────────────────────────────────────────────────

    def _enabled_sorted(self) -> list[WorkerState]:
        """Workers habilitados, prioridad descendente, nombre asc como desempate."""
        return sorted(
            (w for w in self.workers.values() if w.enabled),
            key=lambda w: (-w.priority, w.name),
        )

    def find_workers_for_model(self, model: str) -> list[WorkerState]:
        """Workers que tienen el modelo cargado, en orden de prioridad."""
        return [w for w in self._enabled_sorted() if model in w.models and w.healthy]

    def get_worker(self, name: str) -> WorkerState | None:
        return self.workers.get(name)

    def all_models(self) -> list[dict]:
        """Catálogo unificado (formato OAI /v1/models extendido con `worker`)."""
        out: list[dict] = []
        seen: dict[str, list[str]] = {}  # model -> list of worker names
        for w in self._enabled_sorted():
            if not w.healthy:
                continue
            for m in sorted(w.models):
                seen.setdefault(m, []).append(w.name)
        for model, workers in seen.items():
            out.append({
                "id": model,
                "object": "model",
                "owned_by": workers[0],   # primer worker que lo tiene = "dueño"
                "workers": workers,
            })
        return out

    def snapshot(self) -> list[dict]:
        """Estado de cada worker (para /workers debugging)."""
        return [
            {
                "name": w.name,
                "base_url": w.base_url,
                "priority": w.priority,
                "enabled": w.enabled,
                "healthy": w.healthy,
                "last_check": w.last_check,
                "last_error": w.last_error,
                "models": sorted(w.models),
                "notes": w.notes,
            }
            for w in self._enabled_sorted()
        ]
