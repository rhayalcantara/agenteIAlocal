"""HTTP client al backend OpenAI-compatible (LM Studio gateway).

Lee config de env:
  LMSTUDIO_BASE_URL  (default https://rhayalcantara-002-site2.ntempurl.com/v1)
  LMSTUDIO_API_KEY   (Bearer)
"""
from __future__ import annotations

import os
from typing import AsyncIterator

import httpx
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv("LMSTUDIO_BASE_URL", "https://rhayalcantara-002-site2.ntempurl.com/v1").rstrip("/")
API_KEY = os.getenv("LMSTUDIO_API_KEY", "")
DEFAULT_TIMEOUT = float(os.getenv("ANTHROPIC_GATEWAY_TIMEOUT", "120"))


def _headers() -> dict:
    h = {"Content-Type": "application/json"}
    if API_KEY:
        h["Authorization"] = f"Bearer {API_KEY}"
    return h


async def chat_completion(body: dict) -> dict:
    """Llama POST /chat/completions y retorna el JSON parseado."""
    async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
        r = await client.post(
            f"{BASE_URL}/chat/completions",
            headers=_headers(),
            json=body,
        )
        r.raise_for_status()
        return r.json()


async def chat_completion_stream(body: dict) -> AsyncIterator[str]:
    """Stream SSE de /chat/completions. Devuelve cada chunk JSON crudo (sin 'data:')."""
    payload = dict(body)
    payload["stream"] = True
    async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
        async with client.stream(
            "POST",
            f"{BASE_URL}/chat/completions",
            headers=_headers(),
            json=payload,
        ) as r:
            r.raise_for_status()
            async for line in r.aiter_lines():
                if not line:
                    continue
                if line.startswith("data: "):
                    data = line[6:].strip()
                    if data == "[DONE]":
                        return
                    yield data
