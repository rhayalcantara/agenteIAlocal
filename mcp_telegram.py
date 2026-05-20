"""MCP Server de Telegram — expone el bot como herramientas para Claude Code.

Usa stdio transport. Reutiliza telegram_notifier y telegram_listener.
"""
import os
import sys

# Cargar .env antes de importar módulos que usan variables de entorno
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

from mcp.server.fastmcp import FastMCP

# Importar módulos existentes del proyecto
sys.path.insert(0, os.path.dirname(__file__))
from telegram_notifier_claude import TelegramNotifier
from telegram_listener_claude import TelegramListener

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "agente_core"))

mcp = FastMCP("telegram", instructions="Herramientas para interactuar con Telegram via bot.")

_notifier = TelegramNotifier()
_listener = TelegramListener()

# Cache del modelo Whisper (se carga al primer uso)
_whisper_model = None

def _transcribir(audio_path: str) -> str:
    """Transcribe un archivo de audio a texto usando Whisper."""
    global _whisper_model
    if not audio_path or not os.path.exists(audio_path):
        return ""
    try:
        import whisper
        if _whisper_model is None:
            _whisper_model = whisper.load_model(os.getenv("WHISPER_MODEL", "base"))
        result = _whisper_model.transcribe(audio_path)
        return result["text"].strip()
    except Exception as e:
        return f"[Error transcribiendo audio: {e}]"


@mcp.tool()
def enviar_mensaje(chat_id: int, texto: str) -> str:
    """Envía un mensaje de texto a un chat de Telegram.

    Args:
        chat_id: ID del chat destino
        texto: Texto del mensaje (soporta Markdown)
    """
    msg_id = _notifier.enviar(chat_id, texto)
    if msg_id:
        return f"Mensaje enviado (id: {msg_id})"
    return "Error: no se pudo enviar el mensaje"


@mcp.tool()
def leer_mensajes() -> str:
    """Lee los mensajes pendientes del bot de Telegram.

    Retorna los mensajes nuevos desde la última lectura.
    """
    updates = _listener.get_updates()
    if not updates:
        return "No hay mensajes nuevos."
    mensajes = _listener.extraer_mensajes(updates)
    if not mensajes:
        return "No hay mensajes nuevos."
    from datetime import datetime, timezone
    lines = []
    for m in mensajes:
        user = m.get("user", "?")
        text = m.get("text", "")
        chat_id = m.get("chat_id", "")
        es_voz = m.get("es_voz", False)
        image = " (foto)" if m.get("image_path") else ""
        doc = f" (doc: {m.get('doc_name', '')})" if m.get("doc_path") else ""
        # Transcribir audio si es mensaje de voz
        if es_voz and m.get("audio_path") and not text:
            text = _transcribir(m["audio_path"])
            # Limpiar archivo temporal
            try:
                os.remove(m["audio_path"])
            except Exception:
                pass
        tipo = " (voz)" if es_voz else ""
        date_unix = m.get("date")
        if date_unix:
            dt = datetime.fromtimestamp(date_unix, tz=timezone.utc).astimezone()
            ts = f"[{dt.strftime('%H:%M:%S')}] "
        else:
            ts = ""
        lines.append(f"{ts}[chat:{chat_id}] {user}{tipo}{image}{doc}: {text}")
    return "\n".join(lines)


@mcp.tool()
def enviar_archivo(chat_id: int, ruta: str, caption: str = "") -> str:
    """Envía un archivo o imagen a un chat de Telegram.

    Args:
        chat_id: ID del chat destino
        ruta: Ruta local al archivo
        caption: Texto opcional de acompañamiento
    """
    ok = _notifier.enviar_archivo(chat_id, ruta, caption)
    return "Archivo enviado" if ok else "Error: no se pudo enviar el archivo"


@mcp.tool()
def enviar_voz(chat_id: int, ruta: str, caption: str = "") -> str:
    """Envía un archivo de audio como burbuja de voz en Telegram.

    Args:
        chat_id: ID del chat destino
        ruta: Ruta local al archivo de audio (.ogg ideal, .mp3 también funciona)
        caption: Texto opcional de acompañamiento
    """
    ok = _notifier.enviar_voz(chat_id, ruta, caption)
    return "Voz enviada" if ok else "Error: no se pudo enviar el audio"


@mcp.tool()
def info_bot() -> str:
    """Muestra información del bot de Telegram configurado."""
    token = os.getenv("TELEGRAM_TOKEN", "")
    if not token:
        return "Error: no hay token de Telegram configurado en .env"
    import requests
    try:
        resp = requests.get(f"https://api.telegram.org/bot{token}/getMe", timeout=10)
        data = resp.json()
        if data.get("ok"):
            bot = data["result"]
            return (
                f"Bot: @{bot.get('username', '?')}\n"
                f"Nombre: {bot.get('first_name', '?')}\n"
                f"ID: {bot.get('id', '?')}\n"
                f"Puede unirse a grupos: {bot.get('can_join_groups', '?')}"
            )
        return f"Error API: {data.get('description', 'desconocido')}"
    except Exception as e:
        return f"Error conectando: {e}"


if __name__ == "__main__":
    mcp.run(transport="stdio")
