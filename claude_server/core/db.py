"""SQLite (aiosqlite) — inbox + devices."""
from __future__ import annotations

import os
import json
import secrets
import hashlib
import asyncio
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import aiosqlite

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "chat.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS messages (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    ts          TEXT NOT NULL,
    node_id     TEXT NOT NULL,
    from_node   TEXT NOT NULL,
    direction   TEXT NOT NULL,
    kind        TEXT NOT NULL,
    content     TEXT,
    meta        TEXT
);
CREATE INDEX IF NOT EXISTS idx_messages_node_id ON messages(node_id, id);

CREATE TABLE IF NOT EXISTS devices (
    device_id   TEXT PRIMARY KEY,
    token_hash  TEXT NOT NULL UNIQUE,
    name        TEXT,
    created_at  TEXT,
    last_seen   TEXT
);
"""

_new_message_event: asyncio.Event | None = None


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def get_new_message_event() -> asyncio.Event:
    global _new_message_event
    if _new_message_event is None:
        _new_message_event = asyncio.Event()
    return _new_message_event


def _notify_new_message() -> None:
    ev = get_new_message_event()
    ev.set()
    ev.clear()


async def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript(_SCHEMA)
        await db.commit()


async def bootstrap_default_device(name: str = "default") -> tuple[str, str]:
    """Crea un device 'default' si no existe. Devuelve (device_id, token_plano).

    El token plano solo se devuelve la primera vez. Posteriores llamadas
    devuelven el token desde un archivo cacheado en data/.default_token.
    """
    token_file = DB_PATH.parent / ".default_token"
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT device_id FROM devices WHERE name = ?", (name,)
        )
        row = await cur.fetchone()
        if row:
            device_id = row[0]
            token = token_file.read_text(encoding="utf-8").strip() if token_file.exists() else ""
            return device_id, token

        device_id = f"dev_{secrets.token_hex(6)}"
        token = secrets.token_urlsafe(32)
        await db.execute(
            "INSERT INTO devices(device_id, token_hash, name, created_at) VALUES (?,?,?,?)",
            (device_id, _hash_token(token), name, _now()),
        )
        await db.commit()
        token_file.write_text(token, encoding="utf-8")
        try:
            os.chmod(token_file, 0o600)
        except Exception:
            pass
        return device_id, token


async def get_device_by_token(token: str) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT device_id, name FROM devices WHERE token_hash = ?",
            (_hash_token(token),),
        )
        row = await cur.fetchone()
        if not row:
            return None
        await db.execute(
            "UPDATE devices SET last_seen = ? WHERE device_id = ?",
            (_now(), row["device_id"]),
        )
        await db.commit()
        return {"device_id": row["device_id"], "name": row["name"]}


async def insert_message(
    *,
    node_id: str,
    from_node: str,
    direction: str,
    kind: str,
    content: str | None = None,
    meta: dict | None = None,
) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "INSERT INTO messages(ts, node_id, from_node, direction, kind, content, meta)"
            " VALUES (?,?,?,?,?,?,?)",
            (_now(), node_id, from_node, direction, kind, content, json.dumps(meta) if meta else None),
        )
        await db.commit()
        msg_id = cur.lastrowid
    _notify_new_message()
    return msg_id


async def fetch_after(node_id: str, after_id: int, limit: int = 200) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT id, ts, node_id, from_node, direction, kind, content, meta"
            " FROM messages WHERE node_id = ? AND id > ? ORDER BY id LIMIT ?",
            (node_id, after_id, limit),
        )
        rows = await cur.fetchall()
    out = []
    for r in rows:
        out.append(
            {
                "id": r["id"],
                "ts": r["ts"],
                "node_id": r["node_id"],
                "from_node": r["from_node"],
                "direction": r["direction"],
                "kind": r["kind"],
                "content": r["content"],
                "meta": json.loads(r["meta"]) if r["meta"] else None,
            }
        )
    return out
