from datetime import date
import logging
from sqlalchemy.orm import Session
from app.models.organization import School, AcademicYear, AcademicPeriod
from app.models.security import User
from fastapi import HTTPException
from app.services.rbac_enterprise import (
    ensure_profile, assign_profile, bootstrap_first_administrator, ROLE_PROFILES,
)
from app.services.cloud import ensure_subscription
from app.services.audit import log_action
from app.models.onboarding import SchoolOnboarding

logger = logging.getLogger(__name__)

STEPS = ['school','academic_year','periods','roles','subscription','checklist']

def get_or_create(db: Session, school_id: int) -> SchoolOnboarding:
    state = db.query(SchoolOnboarding).filter_by(school_id=school_id).first()
    if not state:
        state = SchoolOnboarding(school_id=school_id, checklist={s: False for s in STEPS})
        db.add(state); db.flush()
    return state

def _refresh_checklist(db: Session, state: SchoolOnboarding):
    school = db.get(School, state.school_id)
    year = db.query(AcademicYear).filter(AcademicYear.school_id == state.school_id, AcademicYear.is_current.is_(True)).first()
    periods = db.query(AcademicPeriod).filter(AcademicPeriod.academic_year_id == year.id).count() if year else 0
    roles = db.query(__import__('app.models.security', fromlist=['UserPost']).UserPost).join(User).filter(User.school_id == state.school_id).count()
    sub = ensure_subscription(db, state.school_id, commit=False)
    state.checklist = {
        'school': bool(school and school.name),
        'academic_year': bool(year),
        'periods': periods >= 1,
        'roles': roles >= 1,
        'subscription': bool(sub and sub.status in ('trial','active')),
    }
    state.checklist['checklist'] = all(state.checklist.values())
    state.is_completed = state.checklist['checklist']
    state.status = 'completed' if state.is_completed else 'in_progress'
    return state

def bootstrap(db: Session, school_id: int, actor: User, year_label: str, start: date, end: date, period_count: int = 3):
    school = db.get(School, school_id)
    if not school: raise ValueError('Établissement introuvable')
    state = get_or_create(db, school_id)
    year = db.query(AcademicYear).filter(AcademicYear.school_id == school_id, AcademicYear.label == year_label).first()
    if not year:
        db.query(AcademicYear).filter(AcademicYear.school_id == school_id).update({'is_current': False})
        year = AcademicYear(school_id=school_id,label=year_label,start_date=start,end_date=end,is_current=True)
        db.add(year); db.flush()
    else:
        db.query(AcademicYear).filter(AcademicYear.school_id == school_id, AcademicYear.id != year.id).update({'is_current': False})
        year.is_current = True
    existing = db.query(AcademicPeriod).filter(AcademicPeriod.academic_year_id == year.id).count()
    if existing == 0:
        span = max(1, (end-start).days // period_count)
        for i in range(period_count):
            ps = start if i == 0 else date.fromordinal(start.toordinal()+span*i)
            pe = end if i == period_count-1 else date.fromordinal(min(end.toordinal(), start.toordinal()+span*(i+1)-1))
            db.add(AcademicPeriod(academic_year_id=year.id,name=f'Trimestre {i+1}',order_index=i+1,start_date=ps,end_date=pe))
    for code in ROLE_PROFILES:
        ensure_profile(db, school_id, code)
    # Le compte qui lance l'onboarding reçoit explicitement le profil Direction.
    # Cela évite un établissement correctement configuré mais sans utilisateur
    # opérationnel capable de commencer à travailler.
    # Un établissement neuf n'a encore aucun poste attribué : passer par
    # assign_profile lèverait un 403 « profil non délégable » et ferait échouer
    # tout l'onboarding. On amorce donc le premier administrateur, puis on
    # repasse par le chemin contrôlé si des postes existent déjà.
    if actor.school_id == school_id or actor.is_superadmin:
        if bootstrap_first_administrator(db, school_id, actor, 'direction') is None:
            try:
                assign_profile(db, actor, actor.id, 'direction')
            except HTTPException as exc:
                # L'acteur ne peut pas s'auto-élever : l'établissement reste
                # configuré, seule l'attribution de poste est ignorée.
                logger.warning("Attribution automatique du profil direction ignorée pour user=%s school=%s: %s", actor.id, school_id, exc.detail)
    ensure_subscription(db, school_id, commit=False)
    state.current_step = 'checklist'
    _refresh_checklist(db, state)
    db.commit(); db.refresh(state)
    import json
    log_action(db, school_id, actor, 'school.onboarding.bootstrap', 'school', str(school_id), None, json.dumps(state.checklist, ensure_ascii=False))
    return state
