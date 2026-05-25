"""worker_hub — FastAPI app.

Run:  venv/Scripts/python.exe -m uvicorn worker_hub.main:app --host 0.0.0.0 --port 8500
"""
from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import Depends, FastAPI

# .env del root del proyecto (mismo patrón que anthropic_gateway / monitor_bateria)
ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

from worker_hub.core.registry import Registry  # noqa: E402  (después de load_dotenv)
from worker_hub.routes import chat, embeddings, models  # noqa: E402
from worker_hub.routes.auth import require_api_key  # noqa: E402

logging.basicConfig(
    level=os.getenv("WORKER_HUB_LOG", "INFO"),
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
)
log = logging.getLogger("worker_hub")

WORKERS_CONFIG = Path(__file__).parent / "workers.json"


@asynccontextmanager
async def lifespan(app: FastAPI):
    registry = Registry(WORKERS_CONFIG)
    await registry.start()
    app.state.registry = registry
    log.info("worker_hub listo")
    yield
    await registry.stop()


app = FastAPI(
    title="worker_hub",
    description="Pool de workers LLM detrás de un endpoint OpenAI-compatible único.",
    lifespan=lifespan,
)

app.include_router(models.router, tags=["models"])
app.include_router(chat.router, tags=["chat"])
app.include_router(embeddings.router, tags=["embeddings"])


@app.get("/")
async def root():
    return {
        "service": "worker_hub",
        "version": "0.1.0",
        "endpoints": [
            "/v1/models",
            "/v1/chat/completions",
            "/v1/completions",
            "/v1/embeddings",
            "/workers",
            "/health",
        ],
    }


@app.get("/health")
async def health():
    """Liveness del hub mismo (sin auth)."""
    reg = app.state.registry
    healthy = sum(1 for w in reg.workers.values() if w.healthy)
    return {"ok": True, "workers_total": len(reg.workers), "workers_healthy": healthy}


@app.get("/workers", dependencies=[Depends(require_api_key)])
async def workers_state():
    """Estado detallado de cada worker (requiere auth)."""
    return {"workers": app.state.registry.snapshot()}
