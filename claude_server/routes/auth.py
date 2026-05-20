"""Auth bearer-token vs tabla devices."""
from __future__ import annotations

from fastapi import Header, HTTPException, status, Depends

from claude_server.core.db import get_device_by_token


async def require_device(
    authorization: str | None = Header(None),
    x_bridge_token: str | None = Header(None, alias="X-Bridge-Token"),
) -> dict:
    token: str | None = None
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()
    elif x_bridge_token:
        token = x_bridge_token.strip()

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization: Bearer <token> requerido",
        )

    device = await get_device_by_token(token)
    if not device:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido",
        )
    return device


DeviceDep = Depends(require_device)
