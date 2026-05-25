"""GET /v1/models — catálogo unificado."""
from fastapi import APIRouter, Depends, Request

from worker_hub.routes.auth import require_api_key

router = APIRouter()


@router.get("/v1/models", dependencies=[Depends(require_api_key)])
async def list_models(request: Request):
    registry = request.app.state.registry
    return {"object": "list", "data": registry.all_models()}
