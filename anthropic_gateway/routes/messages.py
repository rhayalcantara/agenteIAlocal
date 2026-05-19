"""POST /v1/messages — endpoint estilo Anthropic."""
from __future__ import annotations

import json
import logging
import time
import uuid
from typing import AsyncIterator

import httpx
from fastapi import APIRouter, Header, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse

from anthropic_gateway.core import client, translator

log = logging.getLogger("anthropic_gateway.messages")

router = APIRouter()


def _check_api_key(x_api_key: str | None, authorization: str | None) -> bool:
    """Acepta x-api-key o Authorization: Bearer. Validación contra env opcional."""
    import os
    expected = (os.getenv("ANTHROPIC_GATEWAY_API_KEY") or "").strip()
    if not expected:
        return True  # auth abierta si no se configura
    candidate = (x_api_key or "").strip()
    if not candidate and authorization and authorization.lower().startswith("bearer "):
        candidate = authorization.split(" ", 1)[1].strip()
    return candidate == expected


@router.post("/v1/messages")
async def messages(
    request: Request,
    x_api_key: str | None = Header(None, alias="x-api-key"),
    authorization: str | None = Header(None),
    anthropic_version: str | None = Header(None, alias="anthropic-version"),
):
    if not _check_api_key(x_api_key, authorization):
        raise HTTPException(status_code=401, detail="unauthorized")

    body = await request.json()
    requested_model = body.get("model", "")
    stream = bool(body.get("stream"))

    oai_body = translator.anthropic_to_openai_request(body)
    log.info(
        f"req model={requested_model} → backend model={oai_body.get('model')} "
        f"msgs={len(oai_body.get('messages', []))} stream={stream}"
    )

    if not stream:
        try:
            oai_resp = await client.chat_completion(oai_body)
        except httpx.HTTPStatusError as e:
            return JSONResponse(
                status_code=e.response.status_code,
                content={"type": "error", "error": {"type": "upstream_error",
                                                     "message": e.response.text[:500]}},
            )
        except httpx.RequestError as e:
            raise HTTPException(status_code=502, detail=f"upstream unreachable: {e}")

        return translator.openai_to_anthropic_response(oai_resp, requested_model)

    # ── Streaming SSE Anthropic-style ──────────────────────────────────
    async def event_stream() -> AsyncIterator[bytes]:
        msg_id = f"msg_{uuid.uuid4().hex[:24]}"

        def sse(event: str, data: dict) -> bytes:
            return f"event: {event}\ndata: {json.dumps(data)}\n\n".encode("utf-8")

        # message_start
        yield sse("message_start", {
            "type": "message_start",
            "message": {
                "id": msg_id,
                "type": "message",
                "role": "assistant",
                "model": requested_model,
                "content": [],
                "stop_reason": None,
                "stop_sequence": None,
                "usage": {"input_tokens": 0, "output_tokens": 0},
            },
        })
        # content_block_start (block 0, text)
        yield sse("content_block_start", {
            "type": "content_block_start",
            "index": 0,
            "content_block": {"type": "text", "text": ""},
        })

        stop_reason = "end_turn"
        usage_out = 0
        usage_in = 0

        try:
            async for chunk_raw in client.chat_completion_stream(oai_body):
                try:
                    chunk = json.loads(chunk_raw)
                except json.JSONDecodeError:
                    continue
                choices = chunk.get("choices") or []
                if not choices:
                    # Algunos backends mandan usage en el último chunk sin choices.
                    u = chunk.get("usage") or {}
                    if u:
                        usage_in = u.get("prompt_tokens", usage_in)
                        usage_out = u.get("completion_tokens", usage_out)
                    continue
                ch = choices[0]
                delta = ch.get("delta") or {}
                text_piece = delta.get("content") or ""
                if text_piece:
                    yield sse("content_block_delta", {
                        "type": "content_block_delta",
                        "index": 0,
                        "delta": {"type": "text_delta", "text": text_piece},
                    })
                fr = ch.get("finish_reason")
                if fr:
                    fr = fr.lower()
                    stop_reason = {
                        "stop": "end_turn",
                        "length": "max_tokens",
                        "tool_calls": "tool_use",
                    }.get(fr, "end_turn")
        except httpx.HTTPStatusError as e:
            yield sse("error", {"type": "error", "error": {
                "type": "upstream_error",
                "message": e.response.text[:300],
            }})
            return
        except Exception as e:
            yield sse("error", {"type": "error", "error": {
                "type": "internal_error",
                "message": str(e)[:300],
            }})
            return

        # content_block_stop
        yield sse("content_block_stop", {
            "type": "content_block_stop", "index": 0,
        })
        # message_delta con stop_reason + usage
        yield sse("message_delta", {
            "type": "message_delta",
            "delta": {"stop_reason": stop_reason, "stop_sequence": None},
            "usage": {"output_tokens": usage_out},
        })
        # message_stop
        yield sse("message_stop", {"type": "message_stop"})

    return StreamingResponse(event_stream(), media_type="text/event-stream")
