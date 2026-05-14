"""Cliente helper para el bridge — usable por Claude local o Ranger.

Uso:
    from bridge.client import send, poll, health
    send("hola ranger", to_url="https://claude-ranger.tudominio.workers.dev")
    msgs = poll(from_url="http://localhost:8765")  # leer mi propio inbox
"""
import os
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

DEFAULT_TOKEN = os.getenv("BRIDGE_TOKEN", "")
DEFAULT_LOCAL_URL = os.getenv("BRIDGE_LOCAL_URL", "http://localhost:8765")
DEFAULT_REMOTE_URL = os.getenv("BRIDGE_REMOTE_URL", "")


def send(text: str, *, to_url: str | None = None, from_: str = "claude", meta: dict | None = None, token: str | None = None, timeout: int = 10) -> dict:
    """Envía un mensaje al inbox del otro lado."""
    url = (to_url or DEFAULT_REMOTE_URL).rstrip("/") + "/inbox"
    headers = {"X-Bridge-Token": token or DEFAULT_TOKEN}
    payload = {"text": text, "from_": from_, "meta": meta or {}}
    r = requests.post(url, json=payload, headers=headers, timeout=timeout)
    r.raise_for_status()
    return r.json()


def poll(*, from_url: str | None = None, consume: bool = True, token: str | None = None, timeout: int = 10) -> list[dict]:
    """Lee y consume el inbox propio. Retorna lista de mensajes."""
    url = (from_url or DEFAULT_LOCAL_URL).rstrip("/") + "/poll"
    headers = {"X-Bridge-Token": token or DEFAULT_TOKEN}
    r = requests.get(url, params={"consume": str(consume).lower()}, headers=headers, timeout=timeout)
    r.raise_for_status()
    return r.json().get("messages", [])


def health(url: str | None = None, timeout: int = 5) -> dict:
    """Ping a /health (sin auth) para verificar que el server vive."""
    target = (url or DEFAULT_LOCAL_URL).rstrip("/") + "/health"
    r = requests.get(target, timeout=timeout)
    r.raise_for_status()
    return r.json()
