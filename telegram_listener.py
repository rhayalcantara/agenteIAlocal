"""Listener de Telegram — polling largo con offset persistente."""
import os
import time
import requests
import sys, os; sys.path.insert(0, os.path.join(os.path.dirname(__file__), "agente_core"))
from logger import get_logger

logger = get_logger("telegram_listener")

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
POLL_TIMEOUT = int(os.getenv("TELEGRAM_POLL_TIMEOUT", "30"))
API_BASE = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"


def _get(endpoint: str, params: dict = None, retries: int = 3) -> dict | None:
    url = f"{API_BASE}/{endpoint}"
    for intento in range(retries):
        try:
            resp = requests.get(url, params=params, timeout=POLL_TIMEOUT + 5)
            data = resp.json()
            if data.get("ok"):
                return data
            logger.warning(f"Telegram API error: {data.get('description')}")
            return None
        except Exception as e:
            logger.warning(f"Error GET {endpoint} (intento {intento + 1}): {e}")
            time.sleep(2 ** intento)
    return None


class TelegramListener:
    def __init__(self):
        self._offset = 0

    def get_updates(self) -> list[dict]:
        """Solicita updates con long-polling. Retorna lista de mensajes."""
        params = {
            "offset": self._offset,
            "timeout": POLL_TIMEOUT,
            "allowed_updates": ["message"],
        }
        data = _get("getUpdates", params)
        if not data:
            return []
        updates = data.get("result", [])
        if updates:
            self._offset = updates[-1]["update_id"] + 1
        return updates

    def extraer_mensajes(self, updates: list[dict]) -> list[dict]:
        """Convierte updates crudos en dicts simples {chat_id, user, text, message_id}."""
        mensajes = []
        for upd in updates:
            msg = upd.get("message", {})
            if not msg:
                continue
            chat_id = msg.get("chat", {}).get("id")
            text = msg.get("text", "").strip()
            user = msg.get("from", {}).get("username") or msg.get("from", {}).get("first_name", "?")
            message_id = msg.get("message_id")
            if chat_id and text:
                mensajes.append({
                    "chat_id": chat_id,
                    "user": user,
                    "text": text,
                    "message_id": message_id,
                })
        return mensajes
