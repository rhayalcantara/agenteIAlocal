"""Poller continuo de Telegram para push en tiempo real al Monitor de Claude.

Reutiliza telegram_listener_claude.TelegramListener (mismo offset .telegram_offset_mcp.json
que el MCP) para que sea el ÚNICO consumidor de getUpdates: mientras este script corre,
NO se debe llamar a la tool leer_mensajes del MCP (Telegram tiene una sola cola por bot).

Cada mensaje nuevo se imprime como una línea TG|... en stdout para que el Monitor lo
empuje como notificación. El envío de mensajes sigue disponible vía el MCP (sendMessage
no consume getUpdates, no hay conflicto).
"""
import os
import sys
import time
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(__file__))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

from telegram_listener_claude import TelegramListener

MONITOR_LOG = os.path.join(os.path.dirname(__file__), "telegram_monitor.log")

# ── Whisper lazy para transcribir voces ──────────────────────────────────────
_whisper_model = None

def _get_whisper():
    """Carga Whisper la primera vez que llega una voz. Cachea singleton.
    Si falla (whisper no instalado, modelo no descargable), retorna None."""
    global _whisper_model
    if _whisper_model is not None:
        return _whisper_model
    try:
        import whisper
        size = os.getenv("WHISPER_MODEL", "base")
        print(f"TG_INFO|cargando_whisper_{size}", flush=True)
        _whisper_model = whisper.load_model(size)
        return _whisper_model
    except Exception as e:
        print(f"TG_ERR|whisper_load_fallo: {type(e).__name__}: {e}", flush=True)
        return None


def _transcribir(audio_path: str) -> str:
    """Transcribe un .ogg con Whisper. Retorna '' si falla (no debe romper el poller)."""
    if not audio_path or not os.path.exists(audio_path):
        return ""
    model = _get_whisper()
    if model is None:
        return ""
    try:
        result = model.transcribe(audio_path, language="es", fp16=False)
        return (result.get("text") or "").strip()
    except Exception as e:
        print(f"TG_ERR|transcribir_fallo: {type(e).__name__}: {e}", flush=True)
        return ""


def _limpiar_audio(audio_path: str) -> None:
    """Borra el .ogg temporal tras transcribir. No falla si no existe."""
    if audio_path and os.path.exists(audio_path):
        try:
            os.remove(audio_path)
        except Exception:
            pass


listener = TelegramListener()
print("TELEGRAM_PUSH_READY", flush=True)

while True:
    try:
        updates = listener.get_updates()  # long-poll (timeout configurable, ~30s)
        for m in listener.extraer_mensajes(updates):
            user = m.get("user", "?")
            chat_id = m.get("chat_id", "")
            text = m.get("text", "") or ""
            if m.get("es_voz"):
                audio_path = m.get("audio_path")
                transcripcion = _transcribir(audio_path)
                if transcripcion:
                    text = f"[voz] {transcripcion}"
                else:
                    text = text or "[voz]"
                _limpiar_audio(audio_path)
            elif m.get("image_path"):
                text = text or "[foto]"
            elif m.get("doc_path"):
                text = f"[doc: {m.get('doc_name','')}] {text}".strip()
            date_unix = m.get("date")
            if date_unix:
                dt = datetime.fromtimestamp(date_unix, tz=timezone.utc).astimezone()
                ts = dt.strftime("%H:%M:%S")
            else:
                ts = datetime.now().strftime("%H:%M:%S")
            linea = f"TG|{ts}|{user}|{chat_id}|{text}"
            print(linea, flush=True)
            try:
                with open(MONITOR_LOG, "a", encoding="utf-8") as f:
                    f.write(linea + "\n")
            except Exception:
                pass  # no abortar el poller por un fallo de escritura de log
    except Exception as e:
        print(f"TG_ERR|{e}", flush=True)
        time.sleep(3)
