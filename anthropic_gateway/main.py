"""anthropic_gateway — FastAPI app.

Run:  python -m uvicorn anthropic_gateway.main:app --host 0.0.0.0 --port 8400
"""
from __future__ import annotations

import logging
import os

from fastapi import FastAPI

from anthropic_gateway.routes import messages

logging.basicConfig(
    level=os.getenv("ANTHROPIC_GATEWAY_LOG", "INFO"),
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
)

app = FastAPI(
    title="anthropic_gateway",
    description="Anthropic-compatible /v1/messages proxy → OpenAI chat/completions backend",
)
app.include_router(messages.router, tags=["messages"])


@app.get("/")
async def root():
    return {
        "service": "anthropic_gateway",
        "version": "0.1.0",
        "endpoints": ["/v1/messages", "/health"],
    }


@app.get("/health")
async def health():
    return {"ok": True}
