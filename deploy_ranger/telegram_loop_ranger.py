"""Loop de Telegram para Claude Ranger.

Hace polling del bot Ranger, cuando llega un mensaje ejecuta Claude CLI
y envia la respuesta al grupo por AMBOS bots (Ranger + claudy_rhay_bot)
para que Claude local pueda ver las respuestas.

Uso:
    python3 telegram_loop_ranger.py
"""
import os
import sys
import time
import subprocess
import requests

# Bot del servidor Ranger (token solo desde entorno / .env, NUNCA hardcodeado)
RANGER_TOKEN = os.getenv("RANGER_TELEGRAM_TOKEN", "")
RANGER_API = f"https://api.telegram.org/bot{RANGER_TOKEN}"

# Bot de Claude local (para que el pueda ver las respuestas)
CLAUDY_TOKEN = os.getenv("CLAUDY_TELEGRAM_TOKEN", "")
CLAUDY_API = f"https://api.telegram.org/bot{CLAUDY_TOKEN}"

if not RANGER_TOKEN:
    raise SystemExit("Falta RANGER_TELEGRAM_TOKEN en el entorno/.env")

POLL_INTERVAL = 5
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))

# Fix encoding
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

offset = 0


def get_updates():
    global offset
    try:
        resp = requests.get(f"{RANGER_API}/getUpdates", params={
            "offset": offset, "timeout": 3, "allowed_updates": ["message"]
        }, timeout=10)
        data = resp.json()
        if data.get("ok"):
            updates = data.get("result", [])
            if updates:
                offset = updates[-1]["update_id"] + 1
            return updates
    except Exception as e:
        print(f"Error polling: {e}", flush=True)
    return []


def enviar(chat_id, texto, prefix="[Claude Ranger]"):
    """Envia mensaje por AMBOS bots para que Claude local lo vea."""
    MAX = 4000
    mensaje = f"{prefix} {texto}" if prefix else texto
    partes = [mensaje[i:i+MAX] for i in range(0, len(mensaje), MAX)]

    for parte in partes:
        # Enviar por bot Ranger
        try:
            requests.post(f"{RANGER_API}/sendMessage", json={
                "chat_id": chat_id, "text": parte
            }, timeout=15)
        except Exception as e:
            print(f"Error enviando (ranger): {e}", flush=True)

        # Enviar por bot Claudy (para que Claude local lo vea)
        try:
            requests.post(f"{CLAUDY_API}/sendMessage", json={
                "chat_id": chat_id, "text": parte
            }, timeout=15)
        except Exception as e:
            print(f"Error enviando (claudy): {e}", flush=True)


def ejecutar_claude(prompt, chat_id):
    """Ejecuta Claude CLI con el prompt y retorna la respuesta."""
    try:
        enviar(chat_id, "Procesando...", prefix="[Claude Ranger]")
        result = subprocess.run(
            ["claude", "-p", prompt, "--no-input"],
            capture_output=True, text=True, timeout=300,
            cwd=PROJECT_DIR, encoding="utf-8", errors="replace"
        )
        respuesta = result.stdout.strip()
        if result.stderr:
            respuesta += f"\n\nStderr: {result.stderr[:500]}"
        return respuesta or "(sin respuesta)"
    except subprocess.TimeoutExpired:
        return "Error: timeout de 300s esperando a Claude"
    except FileNotFoundError:
        return "Error: claude CLI no encontrado. Verifica que este instalado y en el PATH"
    except Exception as e:
        return f"Error ejecutando Claude: {e}"


print(f"=== Claude Ranger Loop ===", flush=True)
print(f"Ranger bot: ...{RANGER_TOKEN[-6:]}", flush=True)
print(f"Claudy bot: ...{CLAUDY_TOKEN[-6:]}", flush=True)
print(f"Proyecto: {PROJECT_DIR}", flush=True)
print(f"Esperando mensajes...", flush=True)

while True:
    try:
        updates = get_updates()
        for u in updates:
            msg = u.get("message", {})
            if not msg:
                continue

            chat_id = msg.get("chat", {}).get("id", 0)
            user = msg.get("from", {}).get("first_name", "?")
            text = msg.get("text", "").strip()
            is_bot = msg.get("from", {}).get("is_bot", False)

            # Ignorar mensajes de bots (evitar loops)
            if is_bot:
                continue

            if not text or text.startswith("/start") or text.startswith("/help"):
                continue

            chat_name = msg.get("chat", {}).get("title", f"DM:{user}")
            print(f"[{chat_name}] {user}: {text[:100]}", flush=True)

            # Ejecutar Claude con el mensaje
            respuesta = ejecutar_claude(text, chat_id)
            print(f"  -> Respuesta: {respuesta[:100]}...", flush=True)

            # Enviar respuesta por ambos bots
            enviar(chat_id, respuesta)
            print(f"  -> Enviado a {chat_id} (ambos bots)", flush=True)

    except KeyboardInterrupt:
        print("Loop detenido.", flush=True)
        break
    except Exception as e:
        print(f"Error: {e}", flush=True)
        time.sleep(5)

    time.sleep(POLL_INTERVAL)
