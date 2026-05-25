"""POST /v1/embeddings — proxy con selección por modelo."""
from fastapi import APIRouter, Depends, Header, Request

from worker_hub.core.proxy import forward_sync
from worker_hub.routes.auth import require_api_key

router = APIRouter()


@router.post("/v1/embeddings", dependencies=[Depends(require_api_key)])
async def embeddings(
    request: Request,
    x_worker: str | None = Header(None, alias="x-worker"),
):
    registry = request.app.state.registry
    body = await request.json()
    headers = dict(request.headers)
    # Embeddings no streamea — siempre sync
    return await forward_sync(
        registry=registry,
        path="/embeddings",
        body=body,
        headers=headers,
        force_worker=x_worker,
    )
