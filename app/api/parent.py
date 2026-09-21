from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.deps import get_current_user
from app.models.security import User
from app.services.parent_portal import get_guardian_for_user, linked_students, student_access, child_overview, child_mobile_summary, child_invoices

router = APIRouter(prefix='/api/parent', tags=['Portail parent'])


def guardian_or_403(db, user):
    guardian = get_guardian_for_user(db, user)
    if guardian is None:
        raise HTTPException(status_code=403, detail='Ce compte n’est pas lié à un responsable légal actif')
    return guardian


@router.get('/me')
def parent_me(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    guardian = guardian_or_403(db, current_user)
    return {'id': guardian.id, 'first_name': guardian.first_name, 'last_name': guardian.last_name,
            'relationship_type': guardian.relationship_type, 'school_id': guardian.school_id}


@router.get('/children')
def parent_children(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    guardian = guardian_or_403(db, current_user)
    return [{'id': s.id, 'matricule': s.matricule, 'first_name': s.first_name, 'last_name': s.last_name, 'status': s.status}
            for s in linked_students(db, guardian)]


@router.get('/children/{student_id}/overview')
def parent_child_overview(student_id: int, academic_year_id: int | None = None,
                          db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    guardian = guardian_or_403(db, current_user)
    student = student_access(db, guardian, student_id)
    if student is None:
        raise HTTPException(status_code=404, detail='Élève non lié à ce compte parent')
    return child_overview(db, guardian, student, academic_year_id)


@router.get('/children/{student_id}/mobile-summary')
def parent_child_mobile_summary(student_id: int, academic_year_id: int | None = None,
                                db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    guardian = guardian_or_403(db, current_user)
    student = student_access(db, guardian, student_id)
    if student is None:
        raise HTTPException(status_code=404, detail='Élève non lié à ce compte parent')
    return child_mobile_summary(db, guardian, student, academic_year_id)


@router.get('/children/{student_id}/invoices')
def parent_child_invoices(student_id: int, academic_year_id: int | None = None,
                          db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    guardian = guardian_or_403(db, current_user)
    student = student_access(db, guardian, student_id)
    if student is None:
        raise HTTPException(status_code=404, detail='Élève non lié à ce compte parent')
    return child_invoices(db, guardian, student, academic_year_id)
