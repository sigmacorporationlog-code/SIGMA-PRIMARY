from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.deps import get_current_user
from app.models.security import User
from app.models.students import Student, Guardian, SchoolClass
from app.models.finance import Invoice, Receipt
from app.models.academic import ReportCard
from app.models.documents import IdCard

router = APIRouter(prefix="/api/search", tags=["Recherche globale"])


@router.get("")
def global_search(q: str = Query(min_length=2, max_length=100), limit: int = 20,
                  db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Recherche universelle V3, toujours limitée à l'établissement de l'utilisateur."""
    q = q.strip()
    like = f"%{q}%"
    cap = min(max(limit, 1), 50)
    results = []

    students = db.query(Student).filter(
        Student.school_id == current_user.school_id,
        Student.is_active.is_(True),
        or_(Student.first_name.ilike(like), Student.last_name.ilike(like), Student.matricule.ilike(like)),
    ).limit(cap).all()
    results.extend({"type": "student", "id": s.id, "title": f"{s.last_name} {s.first_name}",
                    "subtitle": f"Matricule {s.matricule}", "action": f"/dashboard/students.html?student_id={s.id}"} for s in students)

    guardians = db.query(Guardian).filter(
        Guardian.school_id == current_user.school_id,
        Guardian.is_active.is_(True),
        or_(Guardian.first_name.ilike(like), Guardian.last_name.ilike(like), Guardian.phone.ilike(like)),
    ).limit(cap).all()
    results.extend({"type": "guardian", "id": g.id, "title": f"{g.last_name} {g.first_name}",
                    "subtitle": g.phone or g.email or "Responsable", "action": f"/dashboard/students.html?guardian_id={g.id}"} for g in guardians)

    classes = db.query(SchoolClass).filter(
        SchoolClass.school_id == current_user.school_id,
        SchoolClass.is_active.is_(True), SchoolClass.name.ilike(like),
    ).limit(cap).all()
    results.extend({"type": "class", "id": c.id, "title": c.name,
                    "subtitle": f"Classe #{c.id}", "action": f"/dashboard/students.html?class_id={c.id}"} for c in classes)

    return {"query": q, "count": len(results), "results": results[:cap]}
