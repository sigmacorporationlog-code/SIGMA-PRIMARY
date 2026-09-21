from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.deps import get_current_user
from app.models.security import User
from app.services import ai as ai_service

router = APIRouter(prefix="/api/ai", tags=["SIGMA Intelligence"])


class AIAsk(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    academic_year_id: int | None = Field(default=None, ge=1)
    academic_period_id: int | None = Field(default=None, ge=1)
    student_id: int | None = Field(default=None, ge=1)
    class_id: int | None = Field(default=None, ge=1)
    grounded_only: bool | None = None


@router.get("/status")
def ai_status(current_user: User = Depends(get_current_user)):
    # L’état du fournisseur IA (provider/modèle) ne doit pas être exposé
    # publiquement. L’endpoint reste disponible à tout utilisateur authentifié.
    return ai_service.status()


@router.post("/ask")
def ai_ask(payload: AIAsk, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    try:
        return ai_service.ask(db, current_user, payload.question, payload.academic_year_id, payload.academic_period_id, payload.student_id, payload.class_id, payload.grounded_only)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=f"Accès refusé: permission requise '{exc.args[0]}'") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
