"""
Heartbeat — escribe periódicamente el estado del agente al disco.

El supervisor lee este archivo para saber si el agente sigue vivo.
"""
import os
import json
import time
import threading

# El heartbeat se guarda en la raíz del proyecto (un nivel arriba de agente_core/)
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HEARTBEAT_FILE = os.path.join(_ROOT, "heartbeat.json")


def escribir(estado: str = "running", extra: dict = None):
    """Escribe/actualiza el archivo heartbeat."""
    datos = {
        "timestamp": time.time(),
        "ts_iso": time.strftime("%Y-%m-%d %H:%M:%S"),
        "estado": estado,
        "pid": os.getpid(),
    }
    if extra:
        datos.update(extra)
    try:
        with open(HEARTBEAT_FILE, "w", encoding="utf-8") as f:
            json.dump(datos, f, indent=2)
    except Exception:
        pass  # nunca romper el agente por un fallo de heartbeat


class HeartbeatThread(threading.Thread):
    """
    Hilo daemon que escribe el heartbeat cada `intervalo` segundos.
    El supervisor detecta un agente congelado si deja de ver actualizaciones.
    """

    def __init__(self, intervalo: int = 30):
        super().__init__(daemon=True, name="heartbeat")
        self.intervalo = intervalo
        self._stop_event = threading.Event()

    def run(self):
        escribir("running")
        while not self._stop_event.wait(self.intervalo):
            escribir("running")

    def detener(self):
        self._stop_event.set()
        escribir("stopped")
