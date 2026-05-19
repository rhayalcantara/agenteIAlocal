"""Dashboard web del Monitor Hub — FastAPI + SSE."""
import os
import sys
import json
import asyncio
from datetime import datetime
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

app = FastAPI(title="Monitor Hub Dashboard")

# Referencia al hub (se inyecta al iniciar)
_hub = None
_message_queue = asyncio.Queue()


def set_hub(hub):
    global _hub
    _hub = hub


@app.get("/", response_class=HTMLResponse)
async def dashboard():
    template_path = os.path.join(os.path.dirname(__file__), "templates", "index.html")
    with open(template_path, "r", encoding="utf-8") as f:
        return f.read()


@app.get("/api/status")
async def status():
    if not _hub:
        return {"error": "Hub no inicializado"}
    stats = _hub.get_stats()
    channels = {}
    for name, plugin in _hub.plugins.items():
        channels[name] = {
            "enabled": plugin.enabled,
            "connected": _hub._stats.get(name, {}).get("connected", False),
            "poll_interval": plugin.poll_interval,
            "messages": _hub._stats.get(name, {}).get("messages", 0),
            "errors": _hub._stats.get(name, {}).get("errors", 0),
        }
    # Canales configurados pero no activos
    for name, cfg in _hub.config.get("channels", {}).items():
        if name not in channels:
            channels[name] = {
                "enabled": cfg.get("enabled", False),
                "connected": False,
                "poll_interval": cfg.get("poll_interval", 0),
                "messages": 0,
                "errors": 0,
            }
    return {
        "running": _hub.running,
        "channels": channels,
        "total_messages": stats["total_messages"],
        "recent_messages": stats["recent_messages"],
    }


@app.get("/api/messages")
async def messages(channel: str = None, limit: int = 50):
    if not _hub:
        return []
    msgs = _hub._message_log[-limit:]
    if channel:
        msgs = [m for m in msgs if m.channel == channel]
    return [{
        "channel": m.channel,
        "chat_name": m.chat_name,
        "user": m.user,
        "text": m.text[:500],
        "type": m.type,
        "priority": m.priority,
        "timestamp": m.timestamp.isoformat(),
    } for m in msgs]


@app.post("/api/channels/{name}/toggle")
async def toggle_channel(name: str):
    if not _hub:
        return {"error": "Hub no inicializado"}
    cfg = _hub.config.get("channels", {}).get(name)
    if not cfg:
        return {"error": f"Canal {name} no encontrado"}
    cfg["enabled"] = not cfg.get("enabled", False)
    # Guardar config
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    config_path = os.path.join(root, "monitor_config.json")
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(_hub.config, f, indent=2, ensure_ascii=False)
    return {"channel": name, "enabled": cfg["enabled"], "message": "Reinicia el hub para aplicar"}


@app.get("/api/config")
async def get_config():
    if not _hub:
        return {}
    return _hub.config


@app.get("/api/events")
async def events(request: Request):
    """Server-Sent Events para mensajes en tiempo real."""
    async def event_stream():
        last_count = len(_hub._message_log) if _hub else 0
        while True:
            if await request.is_disconnected():
                break
            if _hub and len(_hub._message_log) > last_count:
                new_msgs = _hub._message_log[last_count:]
                last_count = len(_hub._message_log)
                for m in new_msgs:
                    data = json.dumps({
                        "channel": m.channel,
                        "chat_name": m.chat_name,
                        "user": m.user,
                        "text": m.text[:500],
                        "type": m.type,
                        "priority": m.priority,
                        "timestamp": m.timestamp.isoformat(),
                    }, ensure_ascii=False)
                    yield f"data: {data}\n\n"
            await asyncio.sleep(1)

    return StreamingResponse(event_stream(), media_type="text/event-stream")
