"""Dependencia FastAPI para validar `x-api-key` o `Authorization: Bearer`."""
import os

from fastapi import Header, HTTPException


def require_api_key(
    x_api_key: str | None = Header(None, alias="x-api-key"),
    authorization: str | None = Header(None),
) -> str:
    """Valida contra WORKER_HUB_API_KEY del env. Si vacío → auth abierta."""
    expected = (os.getenv("WORKER_HUB_API_KEY") or "").strip()
    if not expected:
        return ""
    candidate = (x_api_key or "").strip()
    if not candidate and authorization and authorization.lower().startswith("bearer "):
        candidate = authorization.split(" ", 1)[1].strip()
    if candidate != expected:
        raise HTTPException(status_code=401, detail="unauthorized")
    return candidate
