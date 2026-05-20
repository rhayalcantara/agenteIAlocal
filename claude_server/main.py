"""claude_server — FastAPI app principal.

Run:  uvicorn claude_server.main:app --host 0.0.0.0 --port 8200
"""
from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from claude_server.core.db import bootstrap_default_device, init_db
from claude_server.routes import inbox, stream, upload

logging.basicConfig(
    level=os.getenv("CLAUDE_SERVER_LOG", "INFO"),
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
)
log = logging.getLogger("claude_server")

ROOT = Path(__file__).resolve().parent
STATIC_DIR = ROOT / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    device_id, token = await bootstrap_default_device("default")
    if token:
        log.info(f"Default device ready: {device_id}  token={token}")
    else:
        log.info(f"Default device: {device_id} (token en data/.default_token)")
    yield


app = FastAPI(title="claude_server", lifespan=lifespan)
app.include_router(inbox.router, tags=["inbox"])
app.include_router(stream.router, tags=["stream"])
app.include_router(upload.router, tags=["upload"])
app.mount("/static", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")
app.mount("/uploads", StaticFiles(directory=str(ROOT / "data" / "uploads")), name="uploads")


@app.get("/")
async def root():
    return RedirectResponse(url="/static/index.html")


@app.get("/health")
async def health():
    return {"ok": True, "service": "claude_server"}
