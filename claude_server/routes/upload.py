"""POST /upload — recibe archivos multipart, guarda en data/uploads/, devuelve URL."""
from __future__ import annotations

import secrets
import re
from pathlib import Path
from datetime import datetime

from fastapi import APIRouter, HTTPException, UploadFile, File

from claude_server.routes.auth import DeviceDep

router = APIRouter()

ROOT = Path(__file__).resolve().parent.parent
UPLOAD_DIR = ROOT / "data" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

MAX_BYTES = 25 * 1024 * 1024  # 25 MB por archivo
SAFE_NAME = re.compile(r"[^A-Za-z0-9._-]+")


def _classify(mime: str | None, filename: str) -> str:
    mime = (mime or "").lower()
    if mime.startswith("image/"):
        return "image"
    if mime.startswith("audio/") or filename.lower().endswith((".ogg", ".mp3", ".m4a", ".wav", ".webm")):
        return "audio"
    if mime.startswith("video/"):
        return "video"
    if mime == "application/pdf" or filename.lower().endswith(".pdf"):
        return "pdf"
    return "file"


@router.post("/upload")
async def upload(file: UploadFile = File(...), device=DeviceDep):
    data = await file.read()
    if len(data) == 0:
        raise HTTPException(status_code=400, detail="Archivo vacío")
    if len(data) > MAX_BYTES:
        raise HTTPException(status_code=413, detail=f"Archivo > {MAX_BYTES // 1024 // 1024} MB")

    safe = SAFE_NAME.sub("_", file.filename or "upload")[:80] or "upload"
    prefix = secrets.token_hex(6)
    stamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    name = f"{stamp}_{prefix}_{safe}"
    dest = UPLOAD_DIR / name
    dest.write_bytes(data)

    kind = _classify(file.content_type, file.filename or "")
    return {
        "ok": True,
        "url": f"/uploads/{name}",
        "filename": file.filename,
        "name_stored": name,
        "size": len(data),
        "mime": file.content_type,
        "kind": kind,
        "device": device["device_id"],
    }
