"""Listener de Telegram — polling largo con offset persistente.

Soporta mensajes de texto, voz (voice) y audio.
Los mensajes de voz se descargan automáticamente y se agregan
como 'audio_path' en el dict del mensaje para que el worker
los transcriba con Whisper antes de pasarlos al LLM.
"""
import json
import os
import time
import tempfile
import requests
import sys; sys.path.insert(0, os.path.join(os.path.dirname(__file__), "agente_core"))
from logger import get_logger

logger = get_logger("telegram_listener")

TELEGRAM_TOKEN =  os.getenv("TELEGRAM_TOKEN", "")
POLL_TIMEOUT = int(os.getenv("TELEGRAM_POLL_TIMEOUT", "30"))
API_BASE = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"
FILE_BASE = f"https://api.telegram.org/file/bot{TELEGRAM_TOKEN}"
OFFSET_FILE = os.path.join(os.path.dirname(__file__), ".telegram_offset_mcp.json")


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
        self._offset = self._load_offset()

    def _load_offset(self) -> int:
        try:
            if os.path.exists(OFFSET_FILE):
                with open(OFFSET_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                return int(data.get("offset", 0))
        except Exception as e:
            logger.warning(f"No se pudo cargar offset persistido: {e}")
        return 0

    def _save_offset(self) -> None:
        try:
            with open(OFFSET_FILE, "w", encoding="utf-8") as f:
                json.dump({"offset": self._offset}, f)
        except Exception as e:
            logger.warning(f"No se pudo persistir offset: {e}")

    def get_updates(self) -> list[dict]:
        """Solicita updates con long-polling. Retorna lista de updates."""
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
            self._save_offset()
        return updates

    def descargar_archivo(self, file_id: str, extension: str = ".ogg") -> str | None:
        """Descarga un archivo de Telegram por file_id.

        Returns:
            Ruta al archivo temporal descargado, o None si falla.
        """
        data = _get("getFile", {"file_id": file_id})
        if not data:
            return None
        file_path = data["result"].get("file_path")
        if not file_path:
            return None
        url = f"{FILE_BASE}/{file_path}"
        try:
            resp = requests.get(url, timeout=60)
            if resp.status_code != 200:
                logger.warning(f"Error descargando archivo: HTTP {resp.status_code}")
                return None
            tmp = tempfile.mktemp(suffix=extension, dir=tempfile.gettempdir())
            with open(tmp, "wb") as f:
                f.write(resp.content)
            logger.info(f"Archivo descargado: {tmp} ({len(resp.content)/1024:.1f} KB)")
            return tmp
        except Exception as e:
            logger.error(f"Error descargando {file_id}: {e}")
            return None

    def extraer_mensajes(self, updates: list[dict]) -> list[dict]:
        """Convierte updates crudos en dicts normalizados.

        Campos del dict retornado:
            chat_id, user, text, message_id
            audio_path (str|None) — ruta al audio descargado si es voz
            es_voz (bool)         — True si el mensaje original era de voz
        """
        mensajes = []
        for upd in updates:
            msg = upd.get("message", {})
            if not msg:
                continue

            chat_id = msg.get("chat", {}).get("id")
            user = (msg.get("from", {}).get("username")
                    or msg.get("from", {}).get("first_name", "?"))
            message_id = msg.get("message_id")
            date = msg.get("date")

            if not chat_id:
                continue

            # ── Foto ──────────────────────────────────────────────────────
            photo = msg.get("photo")
            if photo:
                largest = max(photo, key=lambda x: x.get("file_size", 0))
                file_id = largest.get("file_id")
                caption = msg.get("caption", "").strip()
                logger.info(f"Foto recibida de {user}")
                image_path = self.descargar_archivo(file_id, extension=".jpg")
                mensajes.append({
                    "chat_id": chat_id,
                    "user": user,
                    "text": caption or "¿Qué ves en esta imagen?",
                    "message_id": message_id,
                    "date": date,
                    "audio_path": None,
                    "es_voz": False,
                    "image_path": image_path,
                })
                continue

            # ── Mensaje de texto ──────────────────────────────────────────
            text = msg.get("text", "").strip()
            if text:
                mensajes.append({
                    "chat_id": chat_id,
                    "user": user,
                    "text": text,
                    "message_id": message_id,
                    "date": date,
                    "audio_path": None,
                    "es_voz": False,
                    "image_path": None,
                })
                continue

            # ── Mensaje de voz (burbuja de voz) ──────────────────────────
            voice = msg.get("voice")
            if voice:
                file_id = voice.get("file_id")
                duration = voice.get("duration", 0)
                logger.info(f"Voz recibida de {user} ({duration}s)")
                audio_path = self.descargar_archivo(file_id, extension=".ogg")
                mensajes.append({
                    "chat_id": chat_id,
                    "user": user,
                    "text": "",           # se llenará tras transcribir
                    "message_id": message_id,
                    "date": date,
                    "audio_path": audio_path,
                    "es_voz": True,
                })
                continue

            # ── Archivo de audio (mp3, m4a, etc.) ─────────────────────────
            audio = msg.get("audio")
            if audio:
                file_id = audio.get("file_id")
                mime = audio.get("mime_type", "audio/mpeg")
                ext = "." + mime.split("/")[-1] if "/" in mime else ".mp3"
                logger.info(f"Audio recibido de {user} (mime: {mime})")
                audio_path = self.descargar_archivo(file_id, extension=ext)
                mensajes.append({
                    "chat_id": chat_id,
                    "user": user,
                    "text": "",
                    "message_id": message_id,
                    "date": date,
                    "audio_path": audio_path,
                    "es_voz": True,
                    "image_path": None,
                })
                continue

            # ── Documento (pdf, txt, docx, etc.) ──────────────────────────
            document = msg.get("document")
            if document:
                file_id = document.get("file_id")
                file_name = document.get("file_name", "archivo")
                mime = document.get("mime_type", "")
                ext = os.path.splitext(file_name)[1] or ".bin"
                caption = msg.get("caption", "").strip()
                logger.info(f"Documento recibido de {user}: {file_name} ({mime})")
                doc_path = self.descargar_archivo(file_id, extension=ext)
                # El texto que verá el LLM incluye el nombre y caption
                texto_doc = caption or f"Analiza el archivo adjunto: {file_name}"
                mensajes.append({
                    "chat_id": chat_id,
                    "user": user,
                    "text": texto_doc,
                    "message_id": message_id,
                    "date": date,
                    "audio_path": None,
                    "es_voz": False,
                    "image_path": None,
                    "doc_path": doc_path,
                    "doc_name": file_name,
                })
                continue

        return mensajes
