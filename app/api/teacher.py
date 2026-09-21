from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.deps import get_current_user
from app.models.security import User
from app.services.teacher_portal import teacher_overview

router = APIRouter(prefix='/api/teacher', tags=['Portail enseignant'])

@router.get('/overview')
def overview(academic_year_id: int | None = None, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return teacher_overview(db, current_user, academic_year_id)


@router.get('/classes/{class_id}/roster')
def class_roster(class_id: int, academic_year_id: int | None = None, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    from app.services.teacher_portal import teacher_class_roster
    return teacher_class_roster(db, current_user, class_id, academic_year_id)
