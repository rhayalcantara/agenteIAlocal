"""Proxy httpx con soporte sync + streaming + failover."""
from __future__ import annotations

import json
import logging
import os
from typing import AsyncIterator

import httpx
from fastapi import HTTPException
from fastapi.responses import JSONResponse, StreamingResponse

from worker_hub.core.registry import Registry, WorkerState

log = logging.getLogger("worker_hub.proxy")

# Timeout para peticiones LLM (los modelos grandes tardan)
PROXY_TIMEOUT = int(os.getenv("WORKER_HUB_PROXY_TIMEOUT", "300"))
# Headers que NO se propagan al worker (los nuestros)
HOP_BY_HOP = {
    "host", "content-length", "x-api-key", "x-worker",
    "authorization",  # la setea el proxy según la key del worker
}


def _build_headers(req_headers: dict, worker: WorkerState) -> dict:
    """Headers a enviar al worker: limpia los nuestros y agrega su auth si tiene."""
    h = {k: v for k, v in req_headers.items() if k.lower() not in HOP_BY_HOP}
    h["content-type"] = "application/json"
    if worker.api_key:
        h["Authorization"] = f"Bearer {worker.api_key}"
    return h


def _resolve_workers(
    registry: Registry,
    model: str | None,
    force_worker: str | None,
) -> list[WorkerState]:
    """Lista ordenada de workers candidatos. Vacía → error 503."""
    if force_worker:
        w = registry.get_worker(force_worker)
        if not w:
            raise HTTPException(404, f"worker '{force_worker}' no existe")
        if not w.enabled:
            raise HTTPException(503, f"worker '{force_worker}' deshabilitado")
        return [w]
    if not model:
        raise HTTPException(400, "falta 'model' en el body y no se uso x-worker")
    candidates = registry.find_workers_for_model(model)
    if not candidates:
        # Diagnóstico útil: ¿existe el modelo en algún worker, aunque unhealthy?
        unhealthy_with_model = [
            w.name for w in registry.workers.values()
            if model in w.models and not w.healthy
        ]
        if unhealthy_with_model:
            raise HTTPException(
                503,
                f"modelo '{model}' existe en {unhealthy_with_model} pero todos están unhealthy",
            )
        raise HTTPException(404, f"ningún worker tiene el modelo '{model}'")
    return candidates


async def forward_sync(
    *,
    registry: Registry,
    path: str,                # ej. "/chat/completions"
    body: dict,
    headers: dict,
    force_worker: str | None,
) -> JSONResponse:
    """Forward bloqueante con failover en errores 5xx (si no hubo force_worker)."""
    model = body.get("model")
    candidates = _resolve_workers(registry, model, force_worker)

    last_err: tuple[int, str] | None = None
    async with httpx.AsyncClient(timeout=PROXY_TIMEOUT) as client:
        for w in candidates:
            url = f"{w.base_url}{path}"
            try:
                r = await client.post(url, json=body, headers=_build_headers(headers, w))
                if 500 <= r.status_code < 600 and not force_worker and len(candidates) > 1:
                    log.warning(
                        f"worker '{w.name}' devolvio {r.status_code}; probando siguiente"
                    )
                    last_err = (r.status_code, r.text[:300])
                    continue
                # Propagar respuesta tal cual (sea ok o error 4xx del worker)
                content = r.content
                try:
                    payload = json.loads(content)
                except Exception:
                    payload = {"raw": content.decode("utf-8", errors="replace")}
                # Agregar metadata del worker para debugging
                if isinstance(payload, dict):
                    payload.setdefault("_worker_hub", {})["worker"] = w.name
                return JSONResponse(status_code=r.status_code, content=payload)
            except httpx.RequestError as e:
                log.warning(f"worker '{w.name}' unreachable: {e}; probando siguiente")
                last_err = (502, str(e)[:300])
                continue

    code, msg = last_err if last_err else (502, "no workers respondieron")
    raise HTTPException(code, msg)


async def forward_stream(
    *,
    registry: Registry,
    path: str,
    body: dict,
    headers: dict,
    force_worker: str | None,
) -> StreamingResponse:
    """Forward con streaming SSE. NO hace failover mid-stream (sería caótico)."""
    model = body.get("model")
    candidates = _resolve_workers(registry, model, force_worker)
    worker = candidates[0]
    url = f"{worker.base_url}{path}"

    async def gen() -> AsyncIterator[bytes]:
        async with httpx.AsyncClient(timeout=PROXY_TIMEOUT) as client:
            try:
                async with client.stream(
                    "POST", url, json=body, headers=_build_headers(headers, worker)
                ) as r:
                    async for chunk in r.aiter_raw():
                        if chunk:
                            yield chunk
            except httpx.RequestError as e:
                err = json.dumps({"error": {
                    "type": "worker_unreachable",
                    "worker": worker.name,
                    "message": str(e)[:300],
                }}).encode()
                yield b"data: " + err + b"\n\n"

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Worker-Hub-Worker": worker.name,
        },
    )
