"""POST /v1/chat/completions — sync + streaming + failover."""
from fastapi import APIRouter, Depends, Header, Request

from worker_hub.core.proxy import forward_stream, forward_sync
from worker_hub.routes.auth import require_api_key

router = APIRouter()


@router.post("/v1/chat/completions", dependencies=[Depends(require_api_key)])
async def chat_completions(
    request: Request,
    x_worker: str | None = Header(None, alias="x-worker"),
):
    registry = request.app.state.registry
    body = await request.json()
    headers = dict(request.headers)
    stream = bool(body.get("stream"))

    if stream:
        return await forward_stream(
            registry=registry,
            path="/chat/completions",
            body=body,
            headers=headers,
            force_worker=x_worker,
        )
    return await forward_sync(
        registry=registry,
        path="/chat/completions",
        body=body,
        headers=headers,
        force_worker=x_worker,
    )


@router.post("/v1/completions", dependencies=[Depends(require_api_key)])
async def completions(
    request: Request,
    x_worker: str | None = Header(None, alias="x-worker"),
):
    """Legacy completions (no chat). Pasamos por el mismo proxy."""
    registry = request.app.state.registry
    body = await request.json()
    headers = dict(request.headers)
    stream = bool(body.get("stream"))
    if stream:
        return await forward_stream(
            registry=registry, path="/completions", body=body,
            headers=headers, force_worker=x_worker,
        )
    return await forward_sync(
        registry=registry, path="/completions", body=body,
        headers=headers, force_worker=x_worker,
    )
