"""MCP Server de Telegram para Claude del servidor Ranger.

Permite a Claude recibir instrucciones y reportar resultados via Telegram.
Usa stdio transport.
"""
import os
import requests
from mcp.server.fastmcp import FastMCP

TELEGRAM_TOKEN = os.getenv("RANGER_TELEGRAM_TOKEN", "8728278032:AAF9C-pPkQJ2ZCqXcF2JUO3lFQn0fxFvZSU")
API = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

mcp = FastMCP("telegram-ranger", instructions="Bot de Telegram para el servidor Ranger. Recibe instrucciones y reporta resultados.")

_offset = 0


@mcp.tool()
def leer_mensajes() -> str:
    """Lee los mensajes pendientes del bot de Telegram Ranger."""
    global _offset
    try:
        resp = requests.get(f"{API}/getUpdates", params={
            "offset": _offset, "timeout": 5, "allowed_updates": ["message"]
        }, timeout=15)
        data = resp.json()
        if not data.get("ok"):
            return f"Error: {data.get('description', 'desconocido')}"
        updates = data.get("result", [])
        if not updates:
            return "No hay mensajes nuevos."
        _offset = updates[-1]["update_id"] + 1
        lines = []
        for u in updates:
            msg = u.get("message", {})
            user = msg.get("from", {}).get("first_name", "?")
            text = msg.get("text", "")
            chat_id = msg.get("chat", {}).get("id", "")
            lines.append(f"[chat:{chat_id}] {user}: {text}")
        return "\n".join(lines)
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def enviar_mensaje(chat_id: int, texto: str) -> str:
    """Envia un mensaje de texto a un chat de Telegram.

    Args:
        chat_id: ID del chat destino
        texto: Texto del mensaje (soporta Markdown)
    """
    try:
        resp = requests.post(f"{API}/sendMessage", json={
            "chat_id": chat_id, "text": texto
        }, timeout=10)
        data = resp.json()
        if data.get("ok"):
            return f"Mensaje enviado (id: {data['result']['message_id']})"
        return f"Error: {data.get('description', 'desconocido')}"
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def info_bot() -> str:
    """Muestra informacion del bot de Telegram."""
    try:
        resp = requests.get(f"{API}/getMe", timeout=10)
        data = resp.json()
        if data.get("ok"):
            bot = data["result"]
            return (f"Bot: @{bot.get('username', '?')}\n"
                    f"Nombre: {bot.get('first_name', '?')}\n"
                    f"ID: {bot.get('id', '?')}")
        return f"Error: {data.get('description')}"
    except Exception as e:
        return f"Error: {e}"


if __name__ == "__main__":
    mcp.run(transport="stdio")
