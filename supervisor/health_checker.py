"""
Health Checker — determina si el agente core está vivo y respondiendo.

Dos señales combinadas:
  1. Proceso vivo (poll() == None)
  2. Heartbeat fresco (timestamp reciente en heartbeat.json)
"""
import json
import time
import subprocess
from supervisor.config import HEARTBEAT_FILE, HEARTBEAT_TIMEOUT


def leer_heartbeat() -> dict | None:
    """Lee el heartbeat del disco. Retorna None si no existe o está corrupto."""
    try:
        if not HEARTBEAT_FILE.exists():
            return None
        return json.loads(HEARTBEAT_FILE.read_text(encoding="utf-8"))
    except Exception:
        return None


def verificar(proceso: "subprocess.Popen | None" = None) -> dict:
    """
    Verifica el estado del agente combinando proceso + heartbeat.

    Returns:
        dict con:
          - estado:  "ok" | "frozen" | "crashed" | "no_iniciado"
          - detalle: descripción legible para el usuario
          - hb:      datos del heartbeat (o None)
    """
    # ── 1. El proceso terminó inesperadamente ──────────────────────────────────
    if proceso is not None:
        ret = proceso.poll()
        if ret is not None:
            return {
                "estado": "crashed",
                "detalle": f"El proceso terminó con código de salida {ret}.",
                "hb": None,
            }

    # ── 2. Leer heartbeat ──────────────────────────────────────────────────────
    hb = leer_heartbeat()

    if hb is None:
        estado = "no_iniciado" if proceso is None else "no_iniciado"
        return {
            "estado": estado,
            "detalle": "Sin archivo heartbeat — el agente aún no escribió su primer pulso.",
            "hb": None,
        }

    # ── 3. Verificar frescura del heartbeat ────────────────────────────────────
    elapsed = time.time() - hb.get("timestamp", 0)
    if elapsed > HEARTBEAT_TIMEOUT:
        return {
            "estado": "frozen",
            "detalle": (
                f"Sin actualización de heartbeat hace {elapsed:.0f}s "
                f"(umbral: {HEARTBEAT_TIMEOUT}s). "
                f"Último pulso: {hb.get('ts_iso', '?')}."
            ),
            "hb": hb,
        }

    return {
        "estado": "ok",
        "detalle": f"Activo — último pulso hace {elapsed:.0f}s ({hb.get('ts_iso', '?')}).",
        "hb": hb,
    }
