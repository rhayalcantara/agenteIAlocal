"""
Monitor ligero de Telegram para Claude Code.
Hace polling cada 5s y imprime una linea cuando llega un mensaje.
Claude Code usa Monitor para detectar la linea y activar el loop.
Tras detectar actividad, espera 10 minutos antes de seguir monitoreando.
"""
import os
import sys
import time
import requests
from dotenv import load_dotenv

# Fix encoding para Windows
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

TOKEN = os.getenv("TELEGRAM_TOKEN", "")
API = f"https://api.telegram.org/bot{TOKEN}"
POLL_INTERVAL = 5       # segundos entre checks
offset = 0

def get_updates():
    """Peek at updates WITHOUT consuming them (no offset advance).
    Solo mira si hay mensajes pendientes sin marcarlos como leidos.
    El MCP los consumira cuando Claude los lea."""
    global offset
    try:
        resp = requests.get(f"{API}/getUpdates", params={
            "offset": offset, "timeout": 3, "allowed_updates": ["message"]
        }, timeout=10)
        data = resp.json()
        if data.get("ok"):
            updates = data.get("result", [])
            if updates:
                # Avanzar offset para no re-alertar los mismos mensajes
                offset = updates[-1]["update_id"] + 1
            return updates
    except Exception:
        pass
    return []

print("MONITOR_READY", flush=True)

while True:
    updates = get_updates()
    if updates:
        for u in updates:
            msg = u.get("message", {})
            user = msg.get("from", {}).get("first_name", "?")
            text = msg.get("text", "")[:500]
            chat_id = msg.get("chat", {}).get("id", "")
            tipo = "voz" if msg.get("voice") else "foto" if msg.get("photo") else "texto"
            print(f"MENSAJE_NUEVO|{chat_id}|{user}|{tipo}|{text}", flush=True)

    else:
        time.sleep(POLL_INTERVAL)
