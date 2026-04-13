"""Notifier de Telegram — envía mensajes y edita mensajes existentes."""
import os
import time
import requests
import sys, os; sys.path.insert(0, os.path.join(os.path.dirname(__file__), "agente_core"))
from logger import get_logger

logger = get_logger("telegram_notifier")

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
API_BASE = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

# Límite de Telegram por mensaje
MAX_CHARS = 4000


def _post(endpoint: str, payload: dict, retries: int = 3) -> dict | None:
    url = f"{API_BASE}/{endpoint}"
    for intento in range(retries):
        try:
            resp = requests.post(url, json=payload, timeout=15)
            data = resp.json()
            if data.get("ok"):
                return data
            logger.warning(f"Telegram API error [{endpoint}]: {data.get('description')}")
            return None
        except Exception as e:
            logger.warning(f"Error POST {endpoint} (intento {intento + 1}): {e}")
            time.sleep(2 ** intento)
    return None


class TelegramNotifier:
    def enviar(self, chat_id: int, texto: str, parse_mode: str = "Markdown") -> int | None:
        """Envía un mensaje. Si es muy largo lo fragmenta. Devuelve message_id del último mensaje."""
        if not texto:
            return None
        chunks = self._fragmentar(texto)
        last_id = None
        for chunk in chunks:
            payload = {
                "chat_id": chat_id,
                "text": chunk,
                "parse_mode": parse_mode,
            }
            result = _post("sendMessage", payload)
            if result:
                last_id = result["result"]["message_id"]
        return last_id

    def editar(self, chat_id: int, message_id: int, texto: str, parse_mode: str = "Markdown") -> bool:
        """Edita un mensaje existente (para actualizaciones de progreso)."""
        payload = {
            "chat_id": chat_id,
            "message_id": message_id,
            "text": texto[:MAX_CHARS],
            "parse_mode": parse_mode,
        }
        result = _post("editMessageText", payload)
        return result is not None

    def _fragmentar(self, texto: str) -> list[str]:
        if len(texto) <= MAX_CHARS:
            return [texto]
        partes = []
        while texto:
            partes.append(texto[:MAX_CHARS])
            texto = texto[MAX_CHARS:]
        return partes
