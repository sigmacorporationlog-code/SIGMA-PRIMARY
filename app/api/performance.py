from fastapi import APIRouter, Depends
from app.deps import require_permission
from app.services.observability import snapshot

router = APIRouter(prefix="/api/system/performance", tags=["Performance"])

@router.get("/metrics", dependencies=[Depends(require_permission("administration.operations.view"))])
def metrics():
    return snapshot()
