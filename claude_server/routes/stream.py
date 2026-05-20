"""SSE /stream/{node_id} — emite mensajes nuevos en tiempo real."""
from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, Query, Request, Header, HTTPException, status
from sse_starlette.sse import EventSourceResponse

from claude_server.core.db import fetch_after, get_device_by_token, get_new_message_event

router = APIRouter()


async def _resolve_device(
    authorization: str | None,
    token_qs: str | None,
) -> dict:
    """Auth para SSE — acepta Bearer header o ?token=<x> (algunos clientes EventSource no envían headers)."""
    token: str | None = None
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()
    elif token_qs:
        token = token_qs.strip()
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token requerido (Bearer header o ?token=)",
        )
    device = await get_device_by_token(token)
    if not device:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido"
        )
    return device


@router.get("/stream/{node_id}")
async def stream(
    node_id: str,
    request: Request,
    after: int = Query(0, ge=0),
    token: str | None = Query(None),
    authorization: str | None = Header(None),
):
    await _resolve_device(authorization, token)
    new_msg = get_new_message_event()

    async def gen():
        last_id = after
        # Catch-up inicial: cualquier mensaje > after.
        first = await fetch_after(node_id, last_id)
        for m in first:
            yield {"event": "message", "data": json.dumps(m)}
            last_id = max(last_id, m["id"])

        # Loop: espera notificación o timeout para keepalive.
        while True:
            if await request.is_disconnected():
                break
            try:
                await asyncio.wait_for(new_msg.wait(), timeout=15.0)
            except asyncio.TimeoutError:
                yield {"event": "ping", "data": "{}"}
                continue
            rows = await fetch_after(node_id, last_id)
            for m in rows:
                yield {"event": "message", "data": json.dumps(m)}
                last_id = max(last_id, m["id"])

    return EventSourceResponse(gen())
