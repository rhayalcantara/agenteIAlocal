"""Mini-bridge HTTP para comunicación Claude-local ↔ Claude-Ranger.

Cada PC corre una instancia de este server con su propio BRIDGE_TOKEN.
El otro lado hace POST /inbox para depositar mensajes y GET /poll para leerlos.

Exponer al exterior con cloudflared tunnel.
"""
import json
import os
import time
import secrets
from pathlib import Path

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

TOKEN = os.getenv("BRIDGE_TOKEN", "")
STORE = Path(__file__).parent / "bridge_inbox.json"
NODE_NAME = os.getenv("BRIDGE_NODE", "local")  # "local" o "ranger"

if not TOKEN:
    raise RuntimeError("BRIDGE_TOKEN no configurado en .env")

app = FastAPI(title=f"claude-bridge ({NODE_NAME})")


class Msg(BaseModel):
    text: str
    from_: str = "?"
    meta: dict = {}


def _load() -> list[dict]:
    if STORE.exists():
        try:
            return json.loads(STORE.read_text(encoding="utf-8"))
        except Exception:
            return []
    return []


def _save(msgs: list[dict]) -> None:
    STORE.write_text(json.dumps(msgs, ensure_ascii=False, indent=2), encoding="utf-8")


def _auth(token: str | None) -> None:
    if not token or not secrets.compare_digest(token, TOKEN):
        raise HTTPException(401, "bad token")


@app.post("/inbox")
def post_inbox(msg: Msg, x_bridge_token: str | None = Header(default=None)):
    _auth(x_bridge_token)
    msgs = _load()
    entry = {
        "id": int(time.time() * 1000),
        "ts": time.time(),
        "text": msg.text,
        "from": msg.from_,
        "meta": msg.meta,
    }
    msgs.append(entry)
    _save(msgs)
    return {"ok": True, "id": entry["id"], "queued": len(msgs)}


@app.get("/poll")
def get_poll(consume: bool = True, x_bridge_token: str | None = Header(default=None)):
    _auth(x_bridge_token)
    msgs = _load()
    if consume and msgs:
        _save([])
    return {"node": NODE_NAME, "count": len(msgs), "messages": msgs}


@app.get("/health")
def health():
    return {"ok": True, "node": NODE_NAME, "pending": len(_load())}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("BRIDGE_PORT", "8765"))
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
