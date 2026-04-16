"""Notifier de Telegram — envía mensajes, edita mensajes y envía archivos."""
import os
import time
import requests
import sys; sys.path.insert(0, os.path.join(os.path.dirname(__file__), "agente_core"))
from logger import get_logger

logger = get_logger("telegram_notifier")

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "") or os.getenv("TELEGRAM_TOKEN", "")
API_BASE = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

# Límite de Telegram por mensaje
MAX_CHARS = 4000

# Extensiones que Telegram muestra como imagen inline con sendPhoto
_EXTENSIONES_FOTO = {".jpg", ".jpeg", ".png", ".webp"}


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
            if not result and parse_mode:
                # Fallback: reenviar sin formato si falla el parsing de entidades
                logger.warning("Reintentando envío sin parse_mode por error de entidades")
                payload_plain = {"chat_id": chat_id, "text": chunk}
                result = _post("sendMessage", payload_plain)
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
        if not result and parse_mode:
            # Fallback: editar sin formato si falla el parsing de entidades
            payload_plain = {"chat_id": chat_id, "message_id": message_id, "text": texto[:MAX_CHARS]}
            result = _post("editMessageText", payload_plain)
        return result is not None

    def enviar_archivo(self, chat_id: int, ruta: str, caption: str = "") -> bool:
        """Envía un archivo al chat.

        - Imágenes (.jpg, .jpeg, .png, .webp) → sendPhoto (preview inline)
        - Todo lo demás → sendDocument (adjunto descargable)
        Límite Bot API: 50 MB.
        """
        if not os.path.exists(ruta):
            logger.warning(f"Archivo no encontrado: {ruta}")
            return False
        tamaño_mb = os.path.getsize(ruta) / (1024 * 1024)
        if tamaño_mb > 50:
            logger.warning(f"Archivo demasiado grande ({tamaño_mb:.1f} MB > 50 MB): {ruta}")
            return False

        ext = os.path.splitext(ruta)[1].lower()
        es_foto = ext in _EXTENSIONES_FOTO
        endpoint = "sendPhoto" if es_foto else "sendDocument"
        field = "photo" if es_foto else "document"

        try:
            with open(ruta, "rb") as f:
                for intento in range(3):
                    try:
                        resp = requests.post(
                            f"{API_BASE}/{endpoint}",
                            data={"chat_id": chat_id, "caption": caption[:1024]},
                            files={field: f},
                            timeout=120,
                        )
                        data = resp.json()
                        if data.get("ok"):
                            logger.info(f"{'Foto' if es_foto else 'Archivo'} enviado: {ruta} ({tamaño_mb:.1f} MB)")
                            return True
                        logger.warning(f"{endpoint} error: {data.get('description')}")
                        return False
                    except Exception as e:
                        logger.warning(f"Error enviando archivo (intento {intento+1}): {e}")
                        if intento < 2:
                            time.sleep(2 ** intento)
                            f.seek(0)
        except Exception as e:
            logger.error(f"No se pudo abrir el archivo: {e}")
        return False

    def enviar_foto_url(self, chat_id: int, url: str, caption: str = "") -> bool:
        """Envía una foto directamente desde una URL pública (sin descargar)."""
        payload = {
            "chat_id": chat_id,
            "photo": url,
            "caption": caption[:1024],
            "parse_mode": "Markdown",
        }
        result = _post("sendPhoto", payload)
        if result:
            logger.info(f"Foto URL enviada: {url[:80]}")
            return True
        # Fallback: intentar descargar y reenviar como archivo
        try:
            resp = requests.get(url, timeout=15)
            resp.raise_for_status()
            for intento in range(3):
                try:
                    r = requests.post(
                        f"{API_BASE}/sendPhoto",
                        data={"chat_id": chat_id, "caption": caption[:1024], "parse_mode": "Markdown"},
                        files={"photo": ("foto.jpg", resp.content, "image/jpeg")},
                        timeout=30,
                    )
                    data = r.json()
                    if data.get("ok"):
                        logger.info(f"Foto URL enviada (fallback descarga): {url[:80]}")
                        return True
                    logger.warning(f"sendPhoto fallback error: {data.get('description')}")
                    return False
                except Exception as e:
                    logger.warning(f"Error enviando foto (intento {intento+1}): {e}")
                    if intento < 2:
                        time.sleep(2 ** intento)
        except Exception as e:
            logger.error(f"No se pudo descargar imagen: {e}")
        return False

    def enviar_voz(self, chat_id: int, ruta: str, caption: str = "") -> bool:
        """Envía un archivo de audio como burbuja de voz (sendVoice).

        Acepta OGG/Opus (ideal) o MP3 (fallback automático via sendAudio).
        """
        if not os.path.exists(ruta):
            logger.warning(f"Audio no encontrado: {ruta}")
            return False

        # OGG → sendVoice (burbuja con onda de audio)
        # MP3/otro → sendAudio (reproductor de audio)
        ext = os.path.splitext(ruta)[1].lower()
        if ext == ".ogg":
            endpoint, field = "sendVoice", "voice"
        else:
            endpoint, field = "sendAudio", "audio"

        try:
            with open(ruta, "rb") as f:
                for intento in range(3):
                    try:
                        resp = requests.post(
                            f"{API_BASE}/{endpoint}",
                            data={"chat_id": chat_id, "caption": caption[:1024]},
                            files={field: f},
                            timeout=60,
                        )
                        data = resp.json()
                        if data.get("ok"):
                            logger.info(f"Voz enviada ({endpoint}): {ruta}")
                            return True
                        logger.warning(f"{endpoint} error: {data.get('description')}")
                        return False
                    except Exception as e:
                        logger.warning(f"Error enviando voz (intento {intento+1}): {e}")
                        if intento < 2:
                            time.sleep(2 ** intento)
                            f.seek(0)
        except Exception as e:
            logger.error(f"No se pudo abrir audio: {e}")
        return False

    def _fragmentar(self, texto: str) -> list[str]:
        if len(texto) <= MAX_CHARS:
            return [texto]
        partes = []
        while texto:
            partes.append(texto[:MAX_CHARS])
            texto = texto[MAX_CHARS:]
        return partes
