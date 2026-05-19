"""Traductor Anthropic ↔ OpenAI chat-completions.

Schema Anthropic POST /v1/messages:
    {
      "model": "claude-opus-4-7",
      "max_tokens": 1024,
      "system": "...",                # opcional, string o array
      "messages": [
        {"role": "user"|"assistant", "content": str | [blocks]}
      ],
      "temperature": 0.7,             # opcional
      "top_p": 0.9,                   # opcional
      "stop_sequences": [...],        # opcional
      "stream": false,
      "tools": [...],                 # opcional
      "tool_choice": {...}            # opcional
    }

Schema OpenAI chat/completions:
    {
      "model": "...",
      "messages": [
        {"role": "system"|"user"|"assistant"|"tool", "content": str | [blocks]}
      ],
      "max_tokens": 1024,
      "temperature": 0.7,
      "top_p": 0.9,
      "stop": [...],
      "stream": false,
      "tools": [...],
      "tool_choice": "..."
    }

Esta primera versión cubre el path no-streaming, texto puro. Tool-use y
streaming siguen como TODO para fase 2.
"""
from __future__ import annotations

import time
import uuid
from typing import Any


def _flatten_content_blocks(content: Any) -> str:
    """Aplana content que puede venir como string o lista de blocks."""
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return str(content)
    chunks: list[str] = []
    for block in content:
        if isinstance(block, str):
            chunks.append(block)
        elif isinstance(block, dict):
            t = block.get("type")
            if t == "text":
                chunks.append(block.get("text", "") or "")
            elif t == "tool_use":
                # Fase 2: representar como JSON. Por ahora, marker textual.
                chunks.append(f"[tool_use:{block.get('name','?')}]")
            elif t == "tool_result":
                tc = block.get("content")
                if isinstance(tc, list):
                    for sub in tc:
                        if isinstance(sub, dict) and sub.get("type") == "text":
                            chunks.append(sub.get("text", ""))
                elif isinstance(tc, str):
                    chunks.append(tc)
    return "\n".join(c for c in chunks if c)


def anthropic_to_openai_request(body: dict) -> dict:
    """Traduce un body Anthropic /v1/messages a un body OpenAI chat/completions."""
    out_messages: list[dict] = []

    system = body.get("system")
    if system:
        out_messages.append({
            "role": "system",
            "content": _flatten_content_blocks(system),
        })

    for m in body.get("messages", []):
        role = m.get("role", "user")
        content = _flatten_content_blocks(m.get("content", ""))
        out_messages.append({"role": role, "content": content})

    out: dict = {
        "model": body.get("model", ""),
        "messages": out_messages,
        "max_tokens": int(body.get("max_tokens", 1024)),
    }
    if "temperature" in body:
        out["temperature"] = body["temperature"]
    if "top_p" in body:
        out["top_p"] = body["top_p"]
    if body.get("stop_sequences"):
        out["stop"] = body["stop_sequences"]
    if body.get("stream"):
        out["stream"] = True
    return out


def openai_to_anthropic_response(oai: dict, requested_model: str) -> dict:
    """Traduce una respuesta OpenAI chat/completions a una respuesta Anthropic."""
    choice = (oai.get("choices") or [{}])[0]
    msg = choice.get("message") or {}
    text = msg.get("content") or ""

    usage = oai.get("usage") or {}
    finish = (choice.get("finish_reason") or "").lower()
    stop_reason_map = {
        "stop": "end_turn",
        "length": "max_tokens",
        "content_filter": "stop_sequence",
        "tool_calls": "tool_use",
    }
    stop_reason = stop_reason_map.get(finish, "end_turn")

    return {
        "id": oai.get("id") or f"msg_{uuid.uuid4().hex[:24]}",
        "type": "message",
        "role": "assistant",
        "model": requested_model or oai.get("model", ""),
        "content": [{"type": "text", "text": text}] if text else [],
        "stop_reason": stop_reason,
        "stop_sequence": None,
        "usage": {
            "input_tokens": usage.get("prompt_tokens", 0),
            "output_tokens": usage.get("completion_tokens", 0),
        },
        "created_at": int(time.time()),
    }
