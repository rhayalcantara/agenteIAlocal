"""Event emitter — escribe líneas standard a logs/jobs/events.log.

Formato:
    JOB|<evento>|<id>|<name>|<estado>|<k=v>|<k=v>...

Eventos:
    submitted    — job/pipeline registrado, queued
    started      — pasó a running
    step_started — un step de un pipeline arrancó
    step_done    — un step terminó OK
    step_failed  — un step falló (continúa la lógica de DAG)
    done         — job terminó OK
    failed       — job falló
    cancelled    — job cancelado por user/timeout
"""
import os
import threading
from datetime import datetime, timezone
from .db import EVENTS_LOG, LOGS_DIR

_lock = threading.Lock()


def emit(evento: str, job: dict, **extra):
    """Emite un evento standard. `job` es dict con id, name, estado."""
    os.makedirs(LOGS_DIR, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    partes = [
        "JOB",
        evento,
        job.get("id", "?"),
        job.get("name", "?"),
        job.get("estado", "?"),
    ]
    extras_str = "|".join(f"{k}={v}" for k, v in extra.items() if v is not None and v != "")
    if extras_str:
        partes.append(extras_str)
    linea = "|".join(partes)
    # Prefijar el timestamp para análisis temporal
    linea_full = f"{ts} {linea}\n"
    with _lock:
        with open(EVENTS_LOG, "a", encoding="utf-8") as f:
            f.write(linea_full)


def leer_eventos(desde_linea: int = 0, max_lineas: int = 500) -> list:
    """Lee eventos desde la línea N (0-indexed). Para tail incremental."""
    if not os.path.exists(EVENTS_LOG):
        return []
    with open(EVENTS_LOG, "r", encoding="utf-8") as f:
        lineas = f.readlines()
    return [l.rstrip("\n") for l in lineas[desde_linea:desde_linea + max_lineas]]


def total_eventos() -> int:
    if not os.path.exists(EVENTS_LOG):
        return 0
    with open(EVENTS_LOG, "r", encoding="utf-8") as f:
        return sum(1 for _ in f)
