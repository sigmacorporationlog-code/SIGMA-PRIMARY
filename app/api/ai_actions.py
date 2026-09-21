from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.deps import get_current_user
from app.models.security import User
from app.services import ai_actions

router = APIRouter(prefix="/api/ai/actions", tags=["SIGMA AI Actions"])


class AIActionCreate(BaseModel):
    action_type: str = Field(min_length=1, max_length=60)
    title: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=4000)
    payload: dict = Field(default_factory=dict)
    ai_interaction_id: int | None = Field(default=None, ge=1)
    expires_in_minutes: int = Field(default=60, ge=5, le=10080)


class AIActionReject(BaseModel):
    reason: str | None = Field(default=None, max_length=2000)


def _out(item):
    return {
        "id": item.id, "school_id": item.school_id, "created_by_user_id": item.created_by_user_id,
        "approved_by_user_id": item.approved_by_user_id, "ai_interaction_id": item.ai_interaction_id,
        "action_type": item.action_type, "title": item.title, "description": item.description,
        "payload": item.payload_json, "status": item.status, "created_at": item.created_at,
        "expires_at": item.expires_at, "approved_at": item.approved_at, "rejected_at": item.rejected_at,
        "executed_at": item.executed_at, "result": item.result_json, "rejection_reason": item.rejection_reason,
        "execution_enabled": True,
    }


@router.get("/control-center")
def control_center(limit: int = Query(default=20, ge=1, le=100), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    try:
        data = ai_actions.control_center(db, current_user, limit)
        data["proposals"] = [_out(item) for item in data["proposals"]]
        return data
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=f"Accès refusé: permission requise '{exc.args[0]}'") from exc


@router.post("/proposals", status_code=201)
def create(payload: AIActionCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    try:
        return _out(ai_actions.create_proposal(db, current_user, action_type=payload.action_type, title=payload.title,
            description=payload.description, payload=payload.payload, ai_interaction_id=payload.ai_interaction_id,
            expires_in_minutes=payload.expires_in_minutes))
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=f"Accès refusé: permission requise '{exc.args[0]}'") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/proposals")
def list_(status: str | None = Query(default=None), limit: int = Query(default=100, ge=1, le=200), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    try:
        return [_out(x) for x in ai_actions.list_proposals(db, current_user, status, limit)]
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=f"Accès refusé: permission requise '{exc.args[0]}'") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/proposals/{proposal_id}/approve")
def approve(proposal_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    try:
        return _out(ai_actions.approve(db, current_user, proposal_id))
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=f"Accès refusé: permission requise '{exc.args[0]}'") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/proposals/{proposal_id}/reject")
def reject(proposal_id: int, payload: AIActionReject, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    try:
        return _out(ai_actions.reject(db, current_user, proposal_id, payload.reason))
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=f"Accès refusé: permission requise '{exc.args[0]}'") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/proposals/{proposal_id}/execute")
def execute(proposal_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    try:
        return _out(ai_actions.execute(db, current_user, proposal_id))
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=f"Accès refusé: permission requise '{exc.args[0]}'") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
