"""Routes: POST /inbox/{node_id}, GET /poll/{node_id}."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from claude_server.core.db import fetch_after, insert_message
from claude_server.routes.auth import DeviceDep
from claude_server.workers import claude_local

router = APIRouter()


class Attachment(BaseModel):
    url: str
    kind: str  # image | audio | video | pdf | file
    mime: str | None = None
    filename: str | None = None
    meta: dict | None = None  # geo, dimensions, etc.


class InboxPostBody(BaseModel):
    text: str = Field("", description="Texto del mensaje. Puede estar vacío si hay attachments.")
    from_node: str = Field(..., min_length=1)
    meta: dict | None = None
    attachments: list[Attachment] | None = None
    voice_output: bool = False


@router.post("/inbox/{node_id}")
async def post_inbox(node_id: str, body: InboxPostBody, device=DeviceDep):
    if not body.text and not body.attachments:
        raise HTTPException(status_code=400, detail="text o attachments requeridos")

    meta = dict(body.meta or {})
    if body.attachments:
        meta["attachments"] = [a.model_dump() for a in body.attachments]

    msg_id = await insert_message(
        node_id=node_id,
        from_node=body.from_node,
        direction="out",
        kind="text",
        content=body.text or "",
        meta=meta,
    )

    if node_id == "local":
        claude_local.schedule(
            from_node=body.from_node,
            prompt=body.text or "",
            attachments=[a.model_dump() for a in (body.attachments or [])],
            client_meta=body.meta,
            voice_output=body.voice_output,
        )
    elif node_id == "ranger":
        # Fase posterior: relay a Ranger Mac vía bridge HTTP existente.
        await insert_message(
            node_id=body.from_node,
            from_node="system",
            direction="in",
            kind="system",
            content="Routing a Ranger no implementado todavía (fase 5).",
        )

    return {"ok": True, "id": msg_id}


@router.get("/poll/{node_id}")
async def get_poll(node_id: str, after: int = 0, limit: int = 200, device=DeviceDep):
    if limit < 1 or limit > 500:
        raise HTTPException(status_code=400, detail="limit fuera de rango (1..500)")
    rows = await fetch_after(node_id, after_id=after, limit=limit)
    return {"messages": rows, "device": device["device_id"]}
