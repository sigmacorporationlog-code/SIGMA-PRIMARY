from fastapi import APIRouter, Depends
from sqlalchemy import func, case
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.deps import get_current_user, assert_school_access
from app.models.security import User
from app.models.students import ClassMembership, Student, SchoolClass, Level

router = APIRouter(prefix="/api/reports", tags=["Rapports"])


@router.get("/effectif")
def effectif_report(school_id: int, academic_year_id: int, db: Session = Depends(get_db),
                    current_user: User = Depends(get_current_user)):
    assert_school_access(current_user, school_id)
    classes = (
        db.query(SchoolClass.id, SchoolClass.name, SchoolClass.level_id, SchoolClass.capacity)
        .filter(
            SchoolClass.school_id == school_id,
            SchoolClass.academic_year_id == academic_year_id,
            SchoolClass.is_active.is_(True),
        ).all()
    )
    class_ids = [c.id for c in classes]
    counts = {}
    if class_ids:
        rows = (
            db.query(
                ClassMembership.class_id,
                func.count(Student.id),
                func.sum(case((Student.sex == "M", 1), else_=0)),
                func.sum(case((Student.sex == "F", 1), else_=0)),
            )
            .join(Student, Student.id == ClassMembership.student_id)
            .filter(ClassMembership.class_id.in_(class_ids), ClassMembership.left_at.is_(None))
            .group_by(ClassMembership.class_id)
            .all()
        )
        counts = {r[0]: (int(r[1] or 0), int(r[2] or 0), int(r[3] or 0)) for r in rows}

    by_class = []
    for school_class in classes:
        count, male, female = counts.get(school_class.id, (0, 0, 0))
        by_class.append({
            "class_id": school_class.id, "class_name": school_class.name,
            "level_id": school_class.level_id, "effectif": count,
            "garcons": male, "filles": female, "capacite": school_class.capacity,
            "taux_remplissage": round(count / school_class.capacity * 100, 1) if school_class.capacity else None,
        })
    by_level = {}
    for row in by_class:
        level = by_level.setdefault(row["level_id"], {"level_id": row["level_id"], "effectif": 0, "garcons": 0, "filles": 0})
        level["effectif"] += row["effectif"]; level["garcons"] += row["garcons"]; level["filles"] += row["filles"]
    level_names = {l.id: l.name for l in db.query(Level.id, Level.name).filter(Level.school_id == school_id).all()}
    for level in by_level.values():
        level["level_name"] = level_names.get(level["level_id"], "—")
    return {
        "total_effectif": sum(x["effectif"] for x in by_class),
        "total_garcons": sum(x["garcons"] for x in by_class),
        "total_filles": sum(x["filles"] for x in by_class),
        "par_niveau": sorted(by_level.values(), key=lambda x: x["level_name"]),
        "par_classe": sorted(by_class, key=lambda x: x["class_name"]),
    }
