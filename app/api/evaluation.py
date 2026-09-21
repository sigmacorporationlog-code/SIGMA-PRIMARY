from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import Response, FileResponse
from fastapi import status
import io
import zipfile
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.core.database import get_db
from app.core.config import settings
from app.deps import get_current_user, require_permission
from app.models.security import User
from app.models.sync import SyncEntityVersion
from app.models.evaluation import EvaluationFramework, EvaluationDomain, EvaluationCompetency, EvaluationCriterion, RatingScale, EvaluationActivity, EvaluationResult, EvaluationPeriodClosure
from app.schemas.evaluation import FrameworkCreate, DomainCreate, CompetencyCreate, CriterionCreate, ScaleCreate, ActivityCreate, ResultUpsert, ConfigPatch, AppreciationRuleCreate, ResultStateTransition, PeriodFinalizeRequest, PeriodPublishRequest
from app.services.evaluation_engine import rating_for_score, summarize, EVALUATION_STATES, transition_state, calculate_period_results, appreciation_for_percent
from app.services.bulletin_engine import build_bulletin
from app.services.pdf_engine import generate_competency_report_pdf, generate_bulletin_pdf
from app.services.audit import log_action

router = APIRouter(prefix="/api/evaluation", tags=["Évaluations & Carnets"])


def _document_job_dir():
    from app.core.paths import data_dir
    path = data_dir() / "documents" / "jobs"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _run_class_bulletin_export(job_id: int, class_id: int, academic_period_id: int, framework_id: int, language: str):
    from datetime import datetime
    from app.core.database import SessionLocal
    from app.models.document_jobs import DocumentJob
    db = SessionLocal()
    try:
        job = db.get(DocumentJob, job_id)
        if not job:
            return
        job.status = "running"; job.started_at = datetime.utcnow(); db.commit()
        from app.models.students import SchoolClass, ClassMembership, Student
        from app.models.organization import AcademicPeriod, AcademicYear, School
        from app.models.academic import ReportCard
        cls_obj = db.get(SchoolClass, class_id)
        if not cls_obj:
            raise RuntimeError("Classe introuvable")
        cls, period, framework, school, year = _class_period_context(db, class_id, academic_period_id, framework_id, _SystemUser(cls_obj.school_id))
        cards = db.query(ReportCard).filter(ReportCard.class_id == class_id, ReportCard.academic_period_id == academic_period_id, ReportCard.is_published.is_(True)).all()
        members = db.query(ClassMembership).filter(ClassMembership.class_id == class_id, ClassMembership.academic_year_id == cls.academic_year_id, ClassMembership.left_at.is_(None)).all()
        student_ids=[m.student_id for m in members]
        by_student = {s.id:s for s in db.query(Student).filter(Student.id.in_(student_ids)).all()} if student_ids else {}
        job.total = len(cards); db.commit()
        import zipfile, io
        archive = io.BytesIO()
        with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as z:
            for idx, card in enumerate(cards, 1):
                student = by_student.get(card.student_id)
                if not student:
                    continue
                rows = _bulletin_rows(db, student.id, period.id, class_id)
                bulletin = build_bulletin(rows, db, framework_id, "en" if language == "en" else "fr", student=student, class_name=cls.name)
                from app.services.document_verification import create_document_token
                verification_url = f"{settings.PUBLIC_BASE_URL.rstrip('/')}/api/public/documents/verify/{create_document_token('bulletin', card.id, school.id)}"
                pdf = generate_bulletin_pdf(school_name=school.name, ministry_name=school.ministry_name, year_label=year.label, period_name=period.name, student=student, class_name=cls.name, cycle=framework.cycle, section=framework.section, bulletin=bulletin, language="en" if language == "en" else "fr", verification_url=verification_url)
                safe = (student.matricule or str(student.id)).replace("/", "-")
                z.writestr(f"bulletin-{safe}.pdf", pdf)
                job.progress = idx; db.commit()
        path = _document_job_dir() / f"bulletins-{job.id}.zip"
        path.write_bytes(archive.getvalue())
        job.file_path = str(path); job.progress = job.total; job.status = "completed"; job.finished_at = datetime.utcnow(); db.commit()
    except Exception as exc:
        db.rollback()
        job = db.get(DocumentJob, job_id)
        if job:
            job.status = "failed"; job.error_message = str(exc); job.finished_at = datetime.utcnow(); db.commit()
    finally:
        db.close()


class _SystemUser:
    def __init__(self, school_id):
        self.school_id = school_id
        self.is_superadmin = True




def _commit_config(db: Session, obj):
    try:
        db.add(obj)
        db.commit()
        db.refresh(obj)
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Cette configuration existe déjà")
    return obj

def _patch(obj, payload: ConfigPatch, allowed: set[str]):
    values = payload.model_dump(exclude_unset=True)
    for key, value in values.items():
        if key in allowed:
            setattr(obj, key, value)


def school_guard(current_user: User, school_id: int):
    if current_user.is_superadmin:
        return
    if current_user.school_id != school_id:
        raise HTTPException(403, "Établissement non autorisé")


def _check_eval_permission(db, user, permission: str, context=None):
    from app.services.authorization import require_permission as check_permission, PermissionDenied
    try:
        check_permission(db, user, permission, context=context or {})
    except PermissionDenied as exc:
        raise HTTPException(403, str(exc))

def _teacher_assignment_guard(db, user, class_id: int, academic_year_id: int, subject_id: int | None = None):
    if user.is_superadmin:
        return
    from app.services.authorization import user_has_permission
    elevated = any(user_has_permission(db, user, code, {}) for code in (
        "administration.settings.modify", "administration.users.modify", "academic.report_cards.publish"
    ))
    if elevated:
        return
    from app.models.academic import TeacherAssignment
    q = db.query(TeacherAssignment).filter(
        TeacherAssignment.teacher_id == user.id,
        TeacherAssignment.class_id == class_id,
        TeacherAssignment.academic_year_id == academic_year_id,
    )
    if subject_id is not None:
        q = q.filter(TeacherAssignment.subject_id == subject_id)
    if q.first() is None:
        raise HTTPException(403, "Classe/matière non affectée à cet enseignant")


def _check_activity_scope(db, user, activity, write: bool = False):
    from app.models.students import SchoolClass
    from app.models.organization import AcademicPeriod
    cls = db.get(SchoolClass, activity.class_id)
    period = db.get(AcademicPeriod, activity.academic_period_id)
    if cls is None:
        raise HTTPException(404, "Classe introuvable")
    if period is None or period.academic_year_id != cls.academic_year_id:
        raise HTTPException(400, "Période incompatible avec la classe")
    school_guard(user, cls.school_id)
    from app.services.authorization import user_has_permission
    codes = ("evaluation.results.enter", "academic.grades.enter") if write else ("evaluation.results.view", "academic.grades.view")
    if not any(user_has_permission(db, user, code, {"class_id": cls.id, "subject_id": activity.subject_id}) for code in codes):
        raise HTTPException(403, "Permission pédagogique insuffisante")
    _teacher_assignment_guard(db, user, cls.id, cls.academic_year_id, activity.subject_id)
    return cls, period


@router.get("/frameworks")
def frameworks(school_id: int, school_year_id: int | None = None, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    school_guard(current_user, school_id)
    q = db.query(EvaluationFramework).filter(EvaluationFramework.school_id == school_id, EvaluationFramework.is_active.is_(True))
    if school_year_id:
        q = q.filter(EvaluationFramework.school_year_id == school_year_id)
    return [{"id": f.id, "name": f.name, "section": f.section, "cycle": f.cycle, "version": f.version, "active": f.active, "gpa_mode": f.gpa_mode} for f in q.order_by(EvaluationFramework.cycle, EvaluationFramework.section).all()]


@router.post("/frameworks", status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_permission("administration.settings.modify"))])
def create_framework(payload: FrameworkCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    school_guard(current_user, payload.school_id)
    obj = EvaluationFramework(**payload.model_dump())
    db.add(obj); db.commit(); db.refresh(obj)
    return {"id": obj.id, "name": obj.name}


@router.get("/frameworks/{framework_id}")
def framework_detail(framework_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    f = db.get(EvaluationFramework, framework_id)
    if not f: raise HTTPException(404, "Référentiel introuvable")
    school_guard(current_user, f.school_id)
    domains=[]
    for d in sorted(f.domains, key=lambda x:x.display_order):
        comps=[]
        for c in sorted(d.competencies, key=lambda x:x.display_order):
            comps.append({"id":c.id,"code":c.code,"name":c.name,"criteria":[{"id":x.id,"code":x.code,"label":x.label,"mode":x.evaluation_mode,"max_score":x.max_score} for x in sorted(c.criteria,key=lambda x:x.display_order)]})
        domains.append({"id":d.id,"code":d.code,"name":d.name,"weight":d.weight,"competencies":comps})
    scales=[{"id":s.id,"code":s.code,"label":s.label,"min_percent":s.min_percent,"max_percent":s.max_percent,"description":s.description,"grade_point":s.grade_point} for s in sorted(f.scales,key=lambda x:x.display_order)]
    return {"id":f.id,"name":f.name,"section":f.section,"cycle":f.cycle,"version":f.version,"gpa_mode":f.gpa_mode,"domains":domains,"scales":scales}


@router.post("/domains", status_code=201, dependencies=[Depends(require_permission("administration.settings.modify"))])
def create_domain(payload: DomainCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    f=db.get(EvaluationFramework,payload.framework_id)
    if not f: raise HTTPException(404,"Référentiel introuvable")
    school_guard(current_user,f.school_id)
    obj=EvaluationDomain(**payload.model_dump()); return _commit_config(db, obj)

@router.post("/competencies", status_code=201, dependencies=[Depends(require_permission("administration.settings.modify"))])
def create_competency(payload: CompetencyCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    d=db.get(EvaluationDomain,payload.domain_id)
    if not d: raise HTTPException(404,"Domaine introuvable")
    f=db.get(EvaluationFramework,d.framework_id); school_guard(current_user,f.school_id)
    obj=EvaluationCompetency(**payload.model_dump()); return _commit_config(db, obj)

@router.post("/criteria", status_code=201, dependencies=[Depends(require_permission("administration.settings.modify"))])
def create_criterion(payload: CriterionCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    c=db.get(EvaluationCompetency,payload.competency_id)
    if not c: raise HTTPException(404,"Compétence introuvable")
    d=db.get(EvaluationDomain,c.domain_id); f=db.get(EvaluationFramework,d.framework_id); school_guard(current_user,f.school_id)
    obj=EvaluationCriterion(**payload.model_dump()); return _commit_config(db, obj)

@router.post("/scales", status_code=201, dependencies=[Depends(require_permission("administration.settings.modify"))])
def create_scale(payload: ScaleCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    f=db.get(EvaluationFramework,payload.framework_id)
    if not f: raise HTTPException(404,"Référentiel introuvable")
    school_guard(current_user,f.school_id)
    obj=RatingScale(**payload.model_dump()); return _commit_config(db, obj)

@router.patch("/frameworks/{framework_id}", dependencies=[Depends(require_permission("administration.settings.modify"))])
def patch_framework(framework_id: int, payload: ConfigPatch, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    obj=db.get(EvaluationFramework, framework_id)
    if not obj: raise HTTPException(404,"Référentiel introuvable")
    school_guard(current_user,obj.school_id)
    _patch(obj,payload,{"name","version","active","gpa_mode"})
    return _commit_config(db,obj)

@router.patch("/domains/{domain_id}", dependencies=[Depends(require_permission("administration.settings.modify"))])
def patch_domain(domain_id: int, payload: ConfigPatch, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    obj=db.get(EvaluationDomain,domain_id)
    if not obj: raise HTTPException(404,"Domaine introuvable")
    f=db.get(EvaluationFramework,obj.framework_id); school_guard(current_user,f.school_id)
    _patch(obj,payload,{"name","description","weight","display_order"})
    return _commit_config(db,obj)

@router.patch("/competencies/{competency_id}", dependencies=[Depends(require_permission("administration.settings.modify"))])
def patch_competency(competency_id: int, payload: ConfigPatch, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    obj=db.get(EvaluationCompetency,competency_id)
    if not obj: raise HTTPException(404,"Compétence introuvable")
    d=db.get(EvaluationDomain,obj.domain_id); f=db.get(EvaluationFramework,d.framework_id); school_guard(current_user,f.school_id)
    _patch(obj,payload,{"name","description","display_order"})
    return _commit_config(db,obj)

@router.patch("/criteria/{criterion_id}", dependencies=[Depends(require_permission("administration.settings.modify"))])
def patch_criterion(criterion_id: int, payload: ConfigPatch, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    obj=db.get(EvaluationCriterion,criterion_id)
    if not obj: raise HTTPException(404,"Critère introuvable")
    c=db.get(EvaluationCompetency,obj.competency_id); d=db.get(EvaluationDomain,c.domain_id); f=db.get(EvaluationFramework,d.framework_id); school_guard(current_user,f.school_id)
    _patch(obj,payload,{"label","description","evaluation_mode","max_score","weight","display_order"})
    return _commit_config(db,obj)

@router.patch("/scales/{scale_id}", dependencies=[Depends(require_permission("administration.settings.modify"))])
def patch_scale(scale_id: int, payload: ConfigPatch, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    obj=db.get(RatingScale,scale_id)
    if not obj: raise HTTPException(404,"Échelle introuvable")
    school_guard(current_user,db.get(EvaluationFramework,obj.framework_id).school_id)
    _patch(obj,payload,{"label","description","color","grade_point","display_order"})
    return _commit_config(db,obj)

@router.post("/activities", status_code=201)
def create_activity(payload: ActivityCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    from app.models.students import SchoolClass
    from app.models.organization import AcademicPeriod
    cls = db.get(SchoolClass, payload.class_id)
    period = db.get(AcademicPeriod, payload.academic_period_id)
    if not cls:
        raise HTTPException(404, "Classe introuvable")
    if not period:
        raise HTTPException(404, "Période académique introuvable")
    school_guard(current_user, cls.school_id)
    if period.academic_year_id != cls.academic_year_id:
        raise HTTPException(400, "La période et la classe ne relèvent pas de la même année scolaire")
    from app.services.authorization import user_has_permission
    if not any(user_has_permission(db, current_user, code, {"class_id": cls.id, "subject_id": payload.subject_id}) for code in ("evaluation.results.enter", "academic.grades.enter")):
        raise HTTPException(403, "Permission pédagogique insuffisante")
    _teacher_assignment_guard(db, current_user, cls.id, cls.academic_year_id, payload.subject_id)
    if payload.coefficient <= 0:
        raise HTTPException(422, "Le coefficient doit être strictement positif")
    if payload.max_score is not None and payload.max_score <= 0:
        raise HTTPException(422, "Le barème maximal doit être strictement positif")
    if payload.criterion_id:
        criterion = db.get(EvaluationCriterion, payload.criterion_id)
        if not criterion:
            raise HTTPException(404, "Critère introuvable")
        competency = db.get(EvaluationCompetency, criterion.competency_id)
        domain = db.get(EvaluationDomain, competency.domain_id) if competency else None
        framework = db.get(EvaluationFramework, domain.framework_id) if domain else None
        if not framework or framework.school_id != cls.school_id or framework.school_year_id != cls.academic_year_id:
            raise HTTPException(400, "Le critère n'appartient pas au référentiel de la classe")
    obj=EvaluationActivity(**payload.model_dump(), created_by_id=current_user.id)
    db.add(obj); db.commit(); db.refresh(obj); return {"id":obj.id}

@router.get("/activities")
def activities(class_id:int, academic_period_id:int, db:Session=Depends(get_db), current_user:User=Depends(get_current_user)):
    from app.models.students import SchoolClass
    cls=db.get(SchoolClass,class_id)
    if not cls: raise HTTPException(404,"Classe introuvable")
    school_guard(current_user, cls.school_id)
    from app.models.organization import AcademicPeriod
    period = db.get(AcademicPeriod, academic_period_id)
    if period is None or period.academic_year_id != cls.academic_year_id:
        raise HTTPException(400, "Période incompatible avec la classe")
    from app.services.authorization import user_has_permission
    if not any(user_has_permission(db, current_user, code, {"class_id": cls.id}) for code in ("evaluation.results.view", "academic.grades.view")):
        raise HTTPException(403, "Permission pédagogique insuffisante")
    rows=db.query(EvaluationActivity).filter(EvaluationActivity.class_id==class_id, EvaluationActivity.academic_period_id==academic_period_id, EvaluationActivity.is_active.is_(True)).order_by(EvaluationActivity.created_at.desc()).all()
    if not current_user.is_superadmin and not any(user_has_permission(db, current_user, code, {}) for code in ("administration.settings.modify", "administration.users.modify", "academic.report_cards.publish")):
        from app.models.academic import TeacherAssignment
        rows=[a for a in rows if db.query(TeacherAssignment).filter(TeacherAssignment.teacher_id==current_user.id, TeacherAssignment.class_id==class_id, TeacherAssignment.academic_year_id==cls.academic_year_id, TeacherAssignment.subject_id==a.subject_id).first() is not None]
    return [{"id":a.id,"name":a.name,"assessment_type":a.assessment_type,"mode":a.mode,"max_score":a.max_score,"coefficient":a.coefficient,"criterion_id":a.criterion_id} for a in rows]

@router.get("/activities/{activity_id}/results")
def activity_results(activity_id:int, db:Session=Depends(get_db), current_user:User=Depends(get_current_user)):
    a=db.get(EvaluationActivity,activity_id)
    if not a: raise HTTPException(404,"Activité introuvable")
    _check_activity_scope(db, current_user, a, write=False)
    from app.models.students import ClassMembership, Student, SchoolClass
    cls=db.get(SchoolClass,a.class_id)
    if not cls: raise HTTPException(404,"Classe introuvable")
    school_guard(current_user, cls.school_id)
    memberships=db.query(ClassMembership).filter(ClassMembership.class_id==a.class_id,ClassMembership.left_at.is_(None)).all()
    student_ids=[m.student_id for m in memberships]
    students={s.id:s for s in db.query(Student).filter(Student.id.in_(student_ids)).all()} if student_ids else {}
    results={r.student_id:r for r in db.query(EvaluationResult).filter(EvaluationResult.activity_id==a.id, EvaluationResult.student_id.in_(student_ids)).all()} if student_ids else {}
    result_ids=[str(r.id) for r in results.values()]
    versions={v.entity_id:v.version for v in db.query(SyncEntityVersion).filter(SyncEntityVersion.school_id==current_user.school_id, SyncEntityVersion.entity_type=="evaluation_result", SyncEntityVersion.entity_id.in_(result_ids)).all()} if result_ids else {}
    out=[]
    for m in memberships:
        s=students.get(m.student_id); r=results.get(m.student_id)
        out.append({"student_id":m.student_id,"student_name":f"{s.first_name} {s.last_name}" if s else "—","matricule":s.matricule if s else "—","result_id":r.id if r else None,"sync_version":versions.get(str(r.id),0) if r else 0,"activity_id":a.id,"max_score":r.max_score if r and r.max_score is not None else a.max_score,"state":r.state if r else "draft","score":r.score if r else None,"rating_code":r.rating_code if r else None,"is_absent":r.is_absent if r else False,"observation":r.observation if r else "","strengths":r.strengths if r else "","needs_support":r.needs_support if r else ""})
    return sorted(out,key=lambda x:x["student_name"])

@router.post("/activities/{activity_id}/results")
def upsert_results(activity_id:int, payload:list[ResultUpsert], db:Session=Depends(get_db), current_user:User=Depends(get_current_user)):
    a=db.get(EvaluationActivity,activity_id)
    if not a: raise HTTPException(404,"Activité introuvable")
    criterion=db.get(EvaluationCriterion,a.criterion_id) if a.criterion_id else None
    framework=None
    if criterion:
        comp=db.get(EvaluationCompetency,criterion.competency_id); domain=db.get(EvaluationDomain,comp.domain_id); framework=db.get(EvaluationFramework,domain.framework_id)
    out=[]
    rating_scales = []
    if framework and framework.cycle != "nursery":
        rating_scales = db.query(RatingScale).filter(RatingScale.framework_id == framework.id).order_by(RatingScale.display_order).all()
    from app.models.students import Student, ClassMembership
    from app.models.organization import AcademicPeriod
    period = db.get(AcademicPeriod, a.academic_period_id)
    cls = db.get(__import__('app.models.students', fromlist=['SchoolClass']).SchoolClass, a.class_id)
    if not period or not cls or period.academic_year_id != cls.academic_year_id:
        raise HTTPException(400, "Activité académique incohérente")
    _check_activity_scope(db, current_user, a, write=True)
    closure = db.query(EvaluationPeriodClosure).filter(EvaluationPeriodClosure.class_id == cls.id, EvaluationPeriodClosure.academic_period_id == period.id).first()
    if closure and closure.status in ("closed", "published"):
        raise HTTPException(409, "Cette période est clôturée pour cette classe; les résultats sont verrouillés")
    active_students = {m.student_id for m in db.query(ClassMembership).filter(ClassMembership.class_id==a.class_id, ClassMembership.academic_year_id==cls.academic_year_id, ClassMembership.left_at.is_(None)).all()}
    for item in payload:
        if item.student_id not in active_students:
            raise HTTPException(400, f"L'élève {item.student_id} n'est pas inscrit activement dans cette classe")
        max_score=item.max_score if item.max_score is not None else a.max_score
        if item.score is not None and (max_score is None or max_score <= 0):
            raise HTTPException(422, "Un score nécessite un barème maximal positif")
        if item.score is not None and (item.score < 0 or (max_score is not None and item.score > max_score)):
            raise HTTPException(422, "Le score doit être compris entre 0 et le barème maximal")
        if item.is_absent and item.score is not None:
            raise HTTPException(422, "Un élève absent ne peut pas avoir de score")
        r=db.query(EvaluationResult).filter(EvaluationResult.activity_id==activity_id,EvaluationResult.student_id==item.student_id).first()
        if r is None:
            r=EvaluationResult(activity_id=activity_id,student_id=item.student_id)
            db.add(r)
        for field in ["score","max_score","is_absent","observation","strengths","needs_support"]: setattr(r,field,getattr(item,field))
        r.rating_code=None if (framework and framework.cycle == "nursery") else (rating_for_score(db,framework.id,item.score,max_score,scales=rating_scales) if framework else None)
        out.append(r)
    for r in out:
        version = db.query(SyncEntityVersion).filter(SyncEntityVersion.school_id == current_user.school_id, SyncEntityVersion.entity_type == "evaluation_result", SyncEntityVersion.entity_id == str(r.id)).first()
        if version is None:
            version = SyncEntityVersion(school_id=current_user.school_id, entity_type="evaluation_result", entity_id=str(r.id), version=1)
            db.add(version)
        else:
            version.version += 1
    db.commit()
    return [{"id":r.id,"student_id":r.student_id,"rating_code":r.rating_code} for r in out]

@router.get("/frameworks/{framework_id}/appreciation-rules")
def list_appreciation_rules(framework_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    framework = db.get(EvaluationFramework, framework_id)
    if not framework: raise HTTPException(404, "Référentiel introuvable")
    school_guard(current_user, framework.school_id)
    return [{"id": r.id, "code": r.code, "min_percent": r.min_percent, "max_percent": r.max_percent, "text_fr": r.text_fr, "text_en": r.text_en, "priority": r.priority, "active": r.active} for r in framework.appreciation_rules]


@router.post("/appreciation-rules", status_code=201)
def create_appreciation_rule(payload: AppreciationRuleCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    framework = db.get(EvaluationFramework, payload.framework_id)
    if not framework: raise HTTPException(404, "Référentiel introuvable")
    school_guard(current_user, framework.school_id)
    _check_eval_permission(db, current_user, "evaluation.appreciations.modify")
    if payload.min_percent is not None and payload.max_percent is not None and payload.min_percent > payload.max_percent:
        raise HTTPException(422, "Le seuil minimal ne peut pas dépasser le seuil maximal")
    obj = __import__('app.models.evaluation', fromlist=['AppreciationRule']).AppreciationRule(**payload.model_dump())
    db.add(obj); db.commit(); db.refresh(obj)
    log_action(db, current_user.school_id, current_user, "evaluation.appreciation_rule.create", "AppreciationRule", obj.id)
    return {"id": obj.id, "code": obj.code}


@router.post("/results/transition")
def transition_evaluation_results(payload: ResultStateTransition, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if payload.to_state not in EVALUATION_STATES:
        raise HTTPException(400, f"État inconnu. États valides: {EVALUATION_STATES}")
    permission = "evaluation.results.lock" if payload.to_state in ("locked", "published") else "evaluation.results.validate"
    _check_eval_permission(db, current_user, permission)
    updated = 0
    for result_id in payload.result_ids:
        result = db.get(EvaluationResult, result_id)
        if not result: continue
        activity = db.get(EvaluationActivity, result.activity_id)
        if not activity: continue
        cls = __import__('app.models.students', fromlist=['SchoolClass']).SchoolClass
        school_class = db.get(cls, activity.class_id)
        if school_class is None:
            continue
        school_guard(current_user, school_class.school_id)
        _teacher_assignment_guard(db, current_user, school_class.id, school_class.academic_year_id, activity.subject_id)
        if not transition_state(result.state, payload.to_state):
            raise HTTPException(409, f"Transition interdite: {result.state} → {payload.to_state} pour le résultat {result.id}")
        closure = db.query(EvaluationPeriodClosure).filter(EvaluationPeriodClosure.class_id == school_class.id, EvaluationPeriodClosure.academic_period_id == activity.academic_period_id).first()
        if closure and closure.status in ("closed", "published"):
            raise HTTPException(409, "La période est clôturée: aucune transition supplémentaire n’est autorisée")
        old = result.state; result.state = payload.to_state
        if payload.to_state in ("validated", "locked", "published"):
            result.validated_by_id = current_user.id
        log_action(db, current_user.school_id, current_user, "evaluation.result.transition", "EvaluationResult", result.id, old, payload.to_state, commit=False)
        updated += 1
    db.commit()
    return {"status": "ok", "updated": updated, "state": payload.to_state}


@router.get("/students/{student_id}/period-calculation")
def student_period_calculation(student_id: int, academic_period_id: int, framework_id: int, language: str = "fr", db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    from app.models.organization import AcademicPeriod
    from app.models.students import Student
    from app.models.academic import Subject
    student = db.get(Student, student_id); framework = db.get(EvaluationFramework, framework_id); period = db.get(AcademicPeriod, academic_period_id)
    if not student or not framework or not period: raise HTTPException(404, "Données introuvables")
    school_guard(current_user, student.school_id)
    if framework.school_id != student.school_id or period.academic_year_id != framework.school_year_id:
        raise HTTPException(400, "Référentiel et période incompatibles")
    rows = []
    query=(db.query(EvaluationResult, EvaluationActivity, EvaluationCriterion, EvaluationCompetency, Subject)
           .join(EvaluationActivity, EvaluationResult.activity_id==EvaluationActivity.id)
           .outerjoin(EvaluationCriterion, EvaluationActivity.criterion_id==EvaluationCriterion.id)
           .outerjoin(EvaluationCompetency, EvaluationCriterion.competency_id==EvaluationCompetency.id)
           .outerjoin(Subject, EvaluationActivity.subject_id==Subject.id)
           .filter(EvaluationResult.student_id==student_id, EvaluationActivity.academic_period_id==academic_period_id)).all()
    for r,a,criterion,competency,subject in query:
        rows.append({"score":r.score,"max_score":r.max_score or a.max_score,"coefficient":a.coefficient,"is_absent":r.is_absent,"subject_id":a.subject_id,"subject_name":subject.name if subject else None,"competency_id":competency.id if competency else None,"competency_name":competency.name if competency else None,"state":r.state})
    return calculate_period_results(rows, db, framework_id, "en" if language == "en" else "fr")


@router.get("/classes/{class_id}/period-summary")
def class_period_summary(class_id:int, academic_period_id:int, db:Session=Depends(get_db), current_user:User=Depends(get_current_user)):
    """Synthèse contrôlée d'une classe/période : moyenne, évaluations et progression."""
    from app.models.students import SchoolClass, ClassMembership, Student
    from app.models.organization import AcademicPeriod
    cls=db.get(SchoolClass,class_id); period=db.get(AcademicPeriod,academic_period_id)
    if not cls or not period: raise HTTPException(404,"Classe ou période introuvable")
    school_guard(current_user,cls.school_id)
    if period.academic_year_id != cls.academic_year_id: raise HTTPException(400,"Période incompatible avec la classe")
    members=db.query(ClassMembership).filter(ClassMembership.class_id==class_id,ClassMembership.academic_year_id==cls.academic_year_id,ClassMembership.left_at.is_(None)).all()
    student_ids=[m.student_id for m in members]
    students={s.id:s for s in db.query(Student).filter(Student.id.in_(student_ids)).all()} if student_ids else {}
    all_rows=(db.query(EvaluationResult,EvaluationActivity).join(EvaluationActivity,EvaluationResult.activity_id==EvaluationActivity.id)
              .filter(EvaluationResult.student_id.in_(student_ids),EvaluationActivity.class_id==class_id,EvaluationActivity.academic_period_id==academic_period_id,EvaluationResult.state.in_("validated","locked","published")).all()) if student_ids else []
    rows_by_student={}
    for r,a in all_rows:
        rows_by_student.setdefault(r.student_id,[]).append((r,a))
    out=[]
    for m in members:
        student=students.get(m.student_id)
        rows=rows_by_student.get(m.student_id,[])
        data=[{"score":r.score,"max_score":r.max_score or a.max_score,"coefficient":a.coefficient} for r,a in rows]
        summary=summarize(data)
        out.append({"student_id":m.student_id,"student_name":f"{student.first_name} {student.last_name}" if student else "—","average":summary["average"],"evaluations":summary["count"]})
    out.sort(key=lambda x: (x["average"] is None, -(x["average"] or 0), x["student_name"]))
    for i,row in enumerate(out,1): row["rank"]=i if row["average"] is not None else None
    return {"class_id":class_id,"academic_period_id":academic_period_id,"students":out}


def _bulletin_rows(db, student_id: int, academic_period_id: int, class_id: int | None = None):
    q=(db.query(EvaluationResult, EvaluationActivity, EvaluationCriterion, EvaluationCompetency, EvaluationDomain)
       .join(EvaluationActivity, EvaluationResult.activity_id==EvaluationActivity.id)
       .outerjoin(EvaluationCriterion, EvaluationActivity.criterion_id==EvaluationCriterion.id)
       .outerjoin(EvaluationCompetency, EvaluationCriterion.competency_id==EvaluationCompetency.id)
       .outerjoin(EvaluationDomain, EvaluationCompetency.domain_id==EvaluationDomain.id)
       .filter(EvaluationResult.student_id==student_id, EvaluationActivity.academic_period_id==academic_period_id))
    if class_id is not None:
        q=q.filter(EvaluationActivity.class_id==class_id)
    rows=[]
    for r,a,criterion,competency,domain in q.all():
        rows.append({"score":r.score,"max_score":r.max_score or a.max_score,"coefficient":a.coefficient,
                     "is_absent":r.is_absent,"state":r.state,"subject_id":a.subject_id,
                     "subject_name":None,"competency_id":competency.id if competency else None,
                     "competency_name":competency.name if competency else None,
                     "criterion":criterion.label if criterion else a.name,
                     "domain":domain.name if domain else None,"observation":r.observation,
                     "rating_code":r.rating_code})
    # Résolution des matières séparément pour garder la requête simple.
    from app.models.academic import Subject
    subject_ids={r["subject_id"] for r in rows if r["subject_id"] is not None}
    names={s.id:s.name for s in db.query(Subject).filter(Subject.id.in_(subject_ids)).all()} if subject_ids else {}
    for r in rows: r["subject_name"]=names.get(r["subject_id"])
    return rows


@router.get("/students/{student_id}/bulletin-preview")
def bulletin_preview(student_id:int, academic_period_id:int, framework_id:int, language:str="fr", class_id:int|None=None, db:Session=Depends(get_db), current_user:User=Depends(get_current_user)):
    from app.models.students import Student
    student=db.get(Student,student_id); framework=db.get(EvaluationFramework,framework_id)
    if not student or not framework: raise HTTPException(404,"Élève ou référentiel introuvable")
    school_guard(current_user,student.school_id)
    from app.models.organization import AcademicPeriod
    period = db.get(AcademicPeriod, academic_period_id)
    if not period:
        raise HTTPException(404, "Période académique introuvable")
    if framework.school_id != student.school_id or period.academic_year_id != framework.school_year_id:
        raise HTTPException(400,"Référentiel et période incompatibles")
    if class_id is not None:
        from app.models.students import SchoolClass, ClassMembership
        cls = db.get(SchoolClass, class_id)
        if not cls or cls.school_id != student.school_id:
            raise HTTPException(404, "Classe introuvable")
        if cls.academic_year_id != period.academic_year_id:
            raise HTTPException(400, "Classe et période incompatibles")
        membership = db.query(ClassMembership).filter(ClassMembership.student_id == student.id, ClassMembership.class_id == class_id, ClassMembership.academic_year_id == period.academic_year_id, ClassMembership.left_at.is_(None)).first()
        if not membership:
            raise HTTPException(400, "L'élève n'est pas inscrit dans cette classe pour cette année")
    rows=_bulletin_rows(db,student_id,academic_period_id,class_id)
    data=build_bulletin(rows,db,framework_id,"en" if language=="en" else "fr", student=student, class_name=None)
    return {"student_id":student_id,"period_id":academic_period_id,"framework_id":framework_id,"cycle":framework.cycle,"section":framework.section,"bulletin":data}

@router.get("/students/{student_id}/bulletin.pdf")
def student_bulletin_pdf(student_id:int, academic_period_id:int, framework_id:int, language:str="fr", class_id:int|None=None, db:Session=Depends(get_db), current_user:User=Depends(get_current_user)):
    from app.models.students import Student, SchoolClass, ClassMembership
    from app.models.organization import AcademicPeriod, AcademicYear, School
    student=db.get(Student,student_id); framework=db.get(EvaluationFramework,framework_id); period=db.get(AcademicPeriod,academic_period_id)
    if not student or not framework or not period: raise HTTPException(404,"Données du bulletin introuvables")
    school=db.get(School,student.school_id); school_guard(current_user,school.id)
    if framework.school_id != school.id or period.academic_year_id != framework.school_year_id: raise HTTPException(400,"Référentiel et période incompatibles")
    year=db.get(AcademicYear,period.academic_year_id)
    class_name="—"
    if class_id:
        cls=db.get(SchoolClass,class_id)
        if not cls or cls.school_id != school.id: raise HTTPException(404,"Classe introuvable")
        class_name=cls.name
    else:
        membership=db.query(ClassMembership).filter(ClassMembership.student_id==student.id,ClassMembership.academic_year_id==year.id,ClassMembership.left_at.is_(None)).first()
        if membership:
            cls=db.get(SchoolClass,membership.class_id); class_name=cls.name if cls else "—"
            class_id=membership.class_id
    rows=_bulletin_rows(db,student.id,period.id,class_id)
    data=build_bulletin(rows,db,framework_id,"en" if language=="en" else "fr",student=student,class_name=class_name)
    from app.models.academic import ReportCard
    card_query=db.query(ReportCard).filter(ReportCard.student_id==student.id,ReportCard.academic_period_id==period.id,ReportCard.is_published.is_(True))
    if class_id is not None: card_query=card_query.filter(ReportCard.class_id==class_id)
    published_card=card_query.first()
    verification_url=None
    if published_card:
        from app.services.document_verification import create_document_token
        verification_url=f"{settings.PUBLIC_BASE_URL.rstrip('/')}/api/public/documents/verify/{create_document_token('bulletin',published_card.id,school.id)}"
    pdf=generate_bulletin_pdf(school_name=school.name,ministry_name=school.ministry_name,year_label=year.label,period_name=period.name,student=student,class_name=class_name,cycle=framework.cycle,section=framework.section,bulletin=data,language="en" if language=="en" else "fr",verification_url=verification_url)
    return Response(content=pdf,media_type="application/pdf",headers={"Content-Disposition":f'inline; filename="bulletin-{student.matricule or student.id}-{period.order_index}.pdf"'})




def _class_period_context(db, class_id: int, academic_period_id: int, framework_id: int, current_user: User):
    from app.models.students import SchoolClass
    from app.models.organization import AcademicPeriod, School, AcademicYear
    cls = db.get(SchoolClass, class_id); period = db.get(AcademicPeriod, academic_period_id); framework = db.get(EvaluationFramework, framework_id)
    if not cls or not period or not framework:
        raise HTTPException(404, "Classe, période ou référentiel introuvable")
    school_guard(current_user, cls.school_id)
    if period.academic_year_id != cls.academic_year_id or framework.school_id != cls.school_id or framework.school_year_id != cls.academic_year_id:
        raise HTTPException(400, "Classe, période et référentiel incompatibles")
    school = db.get(School, cls.school_id); year = db.get(AcademicYear, cls.academic_year_id)
    return cls, period, framework, school, year


def _student_final_bulletin(db, student_id: int, class_id: int, period_id: int, framework_id: int, language: str):
    rows = _bulletin_rows(db, student_id, period_id, class_id)
    return build_bulletin(rows, db, framework_id, language, class_name=None)


@router.post("/classes/{class_id}/period-finalize")
def finalize_class_period(class_id: int, academic_period_id: int, payload: PeriodFinalizeRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Clôture une période, calcule les bulletins persistés et attribue les rangs si activés."""
    from app.models.students import ClassMembership, Student
    from app.models.academic import ReportCard
    cls, period, framework, school, year = _class_period_context(db, class_id, academic_period_id, payload.framework_id, current_user)
    _check_eval_permission(db, current_user, "evaluation.periods.close")
    closure = db.query(EvaluationPeriodClosure).filter(EvaluationPeriodClosure.class_id == class_id, EvaluationPeriodClosure.academic_period_id == academic_period_id).first()
    if closure and closure.status in ("closed", "published"):
        raise HTTPException(409, "Cette période est déjà clôturée")
    if closure is None:
        closure = EvaluationPeriodClosure(class_id=class_id, academic_period_id=academic_period_id, status="closed", closed_by_id=current_user.id)
        db.add(closure)
    else:
        closure.status = "closed"; closure.closed_by_id = current_user.id
    members = db.query(ClassMembership).filter(ClassMembership.class_id == class_id, ClassMembership.academic_year_id == cls.academic_year_id, ClassMembership.left_at.is_(None)).all()
    student_ids=[m.student_id for m in members]
    students={s.id:s for s in db.query(Student).filter(Student.id.in_(student_ids)).all()} if student_ids else {}
    calculations=[]
    for m in members:
        student=students.get(m.student_id)
        bulletin=_student_final_bulletin(db,m.student_id,class_id,academic_period_id,payload.framework_id,framework.section)
        calculations.append((m.student_id,student,bulletin))
    ranked = sorted([x for x in calculations if x[2].get("average") is not None and x[1] is not None], key=lambda x: (-round(float(x[2]["average"]), 2), (x[1].last_name or ""), (x[1].first_name or "")))
    rank_map={}
    if payload.calculate_rank and framework.cycle != "nursery":
        previous_average=None
        for position,(sid,_,bulletin) in enumerate(ranked,1):
            average=round(float(bulletin["average"]),2)
            if previous_average != average:
                current_rank=position
                previous_average=average
            rank_map[sid]=current_rank
    for sid, student, bulletin in calculations:
        rc=db.query(ReportCard).filter(ReportCard.student_id==sid,ReportCard.academic_period_id==academic_period_id).first()
        if rc is None:
            rc=ReportCard(student_id=sid,class_id=class_id,academic_period_id=academic_period_id)
            db.add(rc)
        rc.general_average=bulletin.get("average")
        rc.class_rank=rank_map.get(sid)
        rc.class_size=len(ranked) if rank_map else None
        app=bulletin.get("appreciation") or {}
        rc.appreciation=app.get("text")
        rc.is_published=False
        calculations_result = bulletin
    db.flush()
    log_action(db,current_user.school_id,current_user,"evaluation.period.close","EvaluationPeriodClosure",closure.id,new_value=f"class={class_id};period={academic_period_id}",commit=False)
    db.commit()
    return {"status":"closed","class_id":class_id,"academic_period_id":academic_period_id,"framework_id":payload.framework_id,"students":len(calculations),"ranked":bool(rank_map)}


@router.post("/classes/{class_id}/period-publish")
def publish_class_period(class_id: int, academic_period_id: int, payload: PeriodPublishRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    from app.models.academic import ReportCard
    closure=db.query(EvaluationPeriodClosure).filter(EvaluationPeriodClosure.class_id==class_id,EvaluationPeriodClosure.academic_period_id==academic_period_id).first()
    if not closure: raise HTTPException(409,"La période doit d'abord être clôturée")
    cls_id=closure.class_id
    from app.models.students import SchoolClass
    cls=db.get(SchoolClass,cls_id); school_guard(current_user,cls.school_id)
    _check_eval_permission(db,current_user,"evaluation.periods.publish")
    if closure.status not in ("closed","published"): raise HTTPException(409,"État de clôture invalide")
    cards=db.query(ReportCard).filter(ReportCard.class_id==class_id,ReportCard.academic_period_id==academic_period_id).all()
    for card in cards: card.is_published=payload.publish
    closure.status="published" if payload.publish else "closed"
    closure.published_by_id=current_user.id if payload.publish else None
    db.commit()
    log_action(db,current_user.school_id,current_user,"evaluation.period.publish","EvaluationPeriodClosure",closure.id,new_value=closure.status)
    return {"status":closure.status,"published_bulletins":sum(1 for c in cards if c.is_published)}


@router.get("/classes/{class_id}/period-report-cards")
def class_period_report_cards(class_id:int, academic_period_id:int, db:Session=Depends(get_db), current_user:User=Depends(get_current_user)):
    from app.models.students import SchoolClass, Student
    cls=db.get(SchoolClass,class_id)
    if not cls: raise HTTPException(404,"Classe introuvable")
    school_guard(current_user,cls.school_id)
    ReportCard=__import__('app.models.academic',fromlist=['ReportCard']).ReportCard
    cards=db.query(ReportCard).filter(ReportCard.class_id==class_id,ReportCard.academic_period_id==academic_period_id).all()
    student_ids=[c.student_id for c in cards]
    students={s.id:s for s in db.query(Student).filter(Student.id.in_(student_ids)).all()} if student_ids else {}
    return [{"id":c.id,"student_id":c.student_id,"student_name":(lambda s:f"{s.first_name} {s.last_name}" if s else "—")(students.get(c.student_id)),"average":c.general_average,"rank":c.class_rank,"class_size":c.class_size,"appreciation":c.appreciation,"published":c.is_published} for c in cards]


@router.get("/classes/{class_id}/period-bulletins.zip")
def class_period_bulletins_zip(class_id:int, academic_period_id:int, framework_id:int, language:str="fr", db:Session=Depends(get_db), current_user:User=Depends(get_current_user)):
    from app.models.students import SchoolClass, ClassMembership, Student
    from app.models.organization import AcademicPeriod, AcademicYear, School
    from app.models.academic import ReportCard
    cls, period, framework, school, year = _class_period_context(db,class_id,academic_period_id,framework_id,current_user)
    cards=db.query(ReportCard).filter(ReportCard.class_id==class_id,ReportCard.academic_period_id==academic_period_id).all()
    if not cards: raise HTTPException(409,"La période doit être clôturée avant la génération de la série de bulletins")
    if any(not c.is_published for c in cards):
        raise HTTPException(409,"Les bulletins de la classe ne sont pas encore publiés")
    members=db.query(ClassMembership).filter(ClassMembership.class_id==class_id,ClassMembership.academic_year_id==cls.academic_year_id,ClassMembership.left_at.is_(None)).all()
    by_student={m.student_id:db.get(Student,m.student_id) for m in members}
    archive=io.BytesIO()
    with zipfile.ZipFile(archive,"w",zipfile.ZIP_DEFLATED) as z:
        for card in cards:
            student=by_student.get(card.student_id)
            if not student: continue
            rows=_bulletin_rows(db,student.id,period.id,class_id)
            bulletin=build_bulletin(rows,db,framework_id,"en" if language=="en" else "fr",student=student,class_name=cls.name)
            from app.services.document_verification import create_document_token
            verification_url=f"{settings.PUBLIC_BASE_URL.rstrip('/')}/api/public/documents/verify/{create_document_token('bulletin',card.id,school.id)}"
            pdf=generate_bulletin_pdf(school_name=school.name,ministry_name=school.ministry_name,year_label=year.label,period_name=period.name,student=student,class_name=cls.name,cycle=framework.cycle,section=framework.section,bulletin=bulletin,language="en" if language=="en" else "fr",verification_url=verification_url)
            safe=(student.matricule or str(student.id)).replace("/","-")
            z.writestr(f"bulletin-{safe}.pdf",pdf)
    return Response(content=archive.getvalue(),media_type="application/zip",headers={"Content-Disposition":f'attachment; filename="SIGMA-bulletins-{cls.name}-{period.order_index}.zip"'})


@router.get("/classes/{class_id}/bulletin-search")
def search_class_bulletins(class_id: int, academic_period_id: int, framework_id: int, q: str = "", db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    from app.models.students import SchoolClass, ClassMembership, Student
    from app.models.academic import ReportCard
    cls = db.get(SchoolClass, class_id)
    if not cls: raise HTTPException(404, "Classe introuvable")
    school_guard(current_user, cls.school_id)
    framework = db.get(EvaluationFramework, framework_id)
    if not framework or framework.school_id != cls.school_id or framework.school_year_id != cls.academic_year_id:
        raise HTTPException(400, "Référentiel incompatible avec la classe")
    cards = db.query(ReportCard).filter(ReportCard.class_id == class_id, ReportCard.academic_period_id == academic_period_id).all()
    members = db.query(ClassMembership).filter(ClassMembership.class_id == class_id, ClassMembership.academic_year_id == cls.academic_year_id, ClassMembership.left_at.is_(None)).all()
    students = {m.student_id: db.get(Student, m.student_id) for m in members}
    needle = q.strip().lower()
    result=[]
    for card in cards:
        s=students.get(card.student_id)
        if not s: continue
        hay=f"{s.first_name or ''} {s.last_name or ''} {s.matricule or ''}".lower()
        if needle and needle not in hay: continue
        result.append({"student_id":s.id,"matricule":s.matricule,"student_name":f"{s.first_name} {s.last_name}","published":card.is_published,"average":card.general_average,"rank":card.class_rank,"pdf":f"/api/evaluation/students/{s.id}/bulletin.pdf?academic_period_id={academic_period_id}&framework_id={framework_id}&class_id={class_id}"})
    return result


@router.post("/classes/{class_id}/period-bulletins/export", status_code=202)
def queue_class_bulletin_export(class_id: int, academic_period_id: int, framework_id: int, background_tasks: BackgroundTasks, language: str = "fr", db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    from app.models.academic import ReportCard
    _class_period_context(db, class_id, academic_period_id, framework_id, current_user)
    cards = db.query(ReportCard).filter(ReportCard.class_id == class_id, ReportCard.academic_period_id == academic_period_id, ReportCard.is_published.is_(True)).all()
    if not cards: raise HTTPException(409, "Aucun bulletin publié à exporter")
    from app.models.document_jobs import DocumentJob
    job=DocumentJob(school_id=current_user.school_id, job_type="class_bulletins_zip", status="queued", total=len(cards), created_by_id=current_user.id)
    db.add(job); db.commit(); db.refresh(job)
    background_tasks.add_task(_run_class_bulletin_export, job.id, class_id, academic_period_id, framework_id, "en" if language == "en" else "fr")
    return {"job_id":job.id,"status":job.status,"total":job.total,"message":"Export lancé en arrière-plan"}


@router.get("/document-jobs/{job_id}")
def document_job_status(job_id:int, db:Session=Depends(get_db), current_user:User=Depends(get_current_user)):
    from app.models.document_jobs import DocumentJob
    job=db.get(DocumentJob,job_id)
    if not job or (job.school_id != current_user.school_id and not current_user.is_superadmin): raise HTTPException(404,"Export introuvable")
    return {"id":job.id,"type":job.job_type,"status":job.status,"progress":job.progress,"total":job.total,"percent":round(job.progress/job.total*100) if job.total else 0,"error":job.error_message,"download":f"/api/evaluation/document-jobs/{job.id}/download" if job.status == "completed" else None}


@router.get("/document-jobs/{job_id}/download")
def download_document_job(job_id:int, db:Session=Depends(get_db), current_user:User=Depends(get_current_user)):
    from app.models.document_jobs import DocumentJob
    job=db.get(DocumentJob,job_id)
    if not job or (job.school_id != current_user.school_id and not current_user.is_superadmin): raise HTTPException(404,"Export introuvable")
    if job.status != "completed" or not job.file_path: raise HTTPException(409,"Export non disponible")
    from pathlib import Path
    path=Path(job.file_path)
    if not path.exists(): raise HTTPException(410,"Fichier d'export expiré")
    return FileResponse(path, media_type="application/zip", filename=f"SIGMA-bulletins-{job.id}.zip")


@router.get("/students/{student_id}/summary")
def student_summary(student_id:int, academic_period_id:int, db:Session=Depends(get_db), current_user:User=Depends(get_current_user)):
    from app.models.students import Student
    student=db.get(Student, student_id)
    if not student: raise HTTPException(404,"Élève introuvable")
    school_guard(current_user, student.school_id)
    rows=(db.query(EvaluationResult,EvaluationActivity).join(EvaluationActivity,EvaluationResult.activity_id==EvaluationActivity.id).filter(EvaluationResult.student_id==student_id,EvaluationActivity.academic_period_id==academic_period_id).all())
    data=[]
    for r,a in rows:
        data.append({"activity_id":a.id,"name":a.name,"mode":a.mode,"score":r.score,"max_score":r.max_score,"rating_code":r.rating_code,"observation":r.observation,"strengths":r.strengths,"needs_support":r.needs_support,"coefficient":a.coefficient})
    return {"student_id":student_id,"period_id":academic_period_id,"summary":summarize(data),"results":data}

def _student_report_data(db, student_id, academic_period_id, framework_id, current_user):
    from app.models.students import Student, SchoolClass, ClassMembership
    from app.models.organization import School, AcademicPeriod, AcademicYear
    student=db.get(Student,student_id); f=db.get(EvaluationFramework,framework_id); period=db.get(AcademicPeriod,academic_period_id)
    if not student or not f or not period: raise HTTPException(404,"Données du carnet introuvables")
    school=db.get(School,student.school_id); school_guard(current_user,school.id)
    if f.school_id != school.id or period.academic_year_id != f.school_year_id:
        raise HTTPException(400,"Référentiel et période incompatibles")
    year=db.get(AcademicYear,period.academic_year_id)
    membership=db.query(ClassMembership).filter(ClassMembership.student_id==student.id,ClassMembership.academic_year_id==year.id,ClassMembership.left_at.is_(None)).first()
    class_name="—"
    if membership:
        cls=db.get(SchoolClass,membership.class_id); class_name=cls.name if cls else "—"
    rows=(db.query(EvaluationResult,EvaluationActivity,EvaluationCriterion,EvaluationCompetency,EvaluationDomain)
          .join(EvaluationActivity,EvaluationResult.activity_id==EvaluationActivity.id)
          .outerjoin(EvaluationCriterion,EvaluationActivity.criterion_id==EvaluationCriterion.id)
          .outerjoin(EvaluationCompetency,EvaluationCriterion.competency_id==EvaluationCompetency.id)
          .outerjoin(EvaluationDomain,EvaluationCompetency.domain_id==EvaluationDomain.id)
          .filter(EvaluationResult.student_id==student.id,EvaluationActivity.academic_period_id==period.id).all())
    results=[{"domain":d.name if d else "", "competency":c.name if c else "", "criterion":cr.label if cr else a.name, "mode":a.mode, "score":r.score, "max_score":r.max_score, "rating":r.rating_code, "observation":r.observation} for r,a,cr,c,d in rows]
    return school,year,period,student,class_name,f,results


@router.get("/students/{student_id}/report.pdf")
def student_report_pdf(student_id:int, academic_period_id:int, framework_id:int, db:Session=Depends(get_db), current_user:User=Depends(get_current_user)):
    school,year,period,student,class_name,f,results = _student_report_data(db,student_id,academic_period_id,framework_id,current_user)
    pdf=generate_competency_report_pdf(school_name=school.name, ministry_name=school.ministry_name, year_label=year.label, period_name=period.name, student=student, class_name=class_name, cycle=f.cycle, section=f.section, results=results, scales=[{"code":s.code,"label":s.label,"description":s.description} for s in f.scales])
    return Response(content=pdf,media_type="application/pdf",headers={"Content-Disposition":f'inline; filename="carnet-{student.matricule}-{period.order_index}.pdf"'})


@router.get("/classes/{class_id}/reports.zip")
def class_reports_zip(class_id:int, academic_period_id:int, framework_id:int, db:Session=Depends(get_db), current_user:User=Depends(get_current_user)):
    """Génère tous les carnets PDF de la classe dans une seule archive ZIP."""
    from app.models.students import SchoolClass, ClassMembership, Student
    cls=db.get(SchoolClass,class_id)
    f=db.get(EvaluationFramework,framework_id)
    if not cls or not f: raise HTTPException(404,"Classe ou référentiel introuvable")
    school_guard(current_user, cls.school_id)
    if f.school_id != cls.school_id or f.school_year_id != cls.academic_year_id:
        raise HTTPException(400,"Référentiel incompatible avec la classe")
    members=(db.query(ClassMembership).filter(ClassMembership.class_id==class_id,ClassMembership.academic_year_id==cls.academic_year_id,ClassMembership.left_at.is_(None)).all())
    buffer=io.BytesIO()
    with zipfile.ZipFile(buffer,"w",zipfile.ZIP_DEFLATED) as archive:
        for m in members:
            student=db.get(Student,m.student_id)
            if not student or student.status not in ("active","conditional"):
                continue
            school,year,period,student,class_name,f,results=_student_report_data(db,student.id,academic_period_id,framework_id,current_user)
            pdf=generate_competency_report_pdf(school_name=school.name, ministry_name=school.ministry_name, year_label=year.label, period_name=period.name, student=student, class_name=class_name, cycle=f.cycle, section=f.section, results=results, scales=[{"code":s.code,"label":s.label,"description":s.description} for s in f.scales])
            safe=(student.matricule or str(student.id)).replace("/","-").replace("\\","-")
            archive.writestr(f"{safe}_{period.order_index}.pdf",pdf)
    buffer.seek(0)
    return Response(content=buffer.getvalue(),media_type="application/zip",headers={"Content-Disposition":f'attachment; filename="carnets-classe-{class_id}-periode-{academic_period_id}.zip"'})

@router.get("/classes/{class_id}/teacher-workspace")
def teacher_workspace(class_id: int, academic_period_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Espace enseignant action-first: activités, couverture de saisie et élèves à surveiller."""
    from app.models.students import SchoolClass, ClassMembership, Student
    from app.models.organization import AcademicPeriod
    from app.services.pedagogy_engine import class_risk_snapshot

    cls = db.get(SchoolClass, class_id)
    period = db.get(AcademicPeriod, academic_period_id)
    if not cls or not period:
        raise HTTPException(404, "Classe ou période introuvable")
    school_guard(current_user, cls.school_id)
    if period.academic_year_id != cls.academic_year_id:
        raise HTTPException(400, "Période incompatible avec la classe")
    # Un enseignant ne doit jamais pouvoir utiliser cet endpoint comme
    # raccourci vers une classe quelconque de son établissement.
    # La consultation du workspace est bornée à ses affectations réelles.
    if not current_user.is_superadmin:
        from app.models.academic import TeacherAssignment
        assigned = db.query(TeacherAssignment).filter(
            TeacherAssignment.teacher_id == current_user.id,
            TeacherAssignment.class_id == class_id,
            TeacherAssignment.academic_year_id == cls.academic_year_id,
        ).first()
        if assigned is None:
            raise HTTPException(403, "Classe non affectée à cet enseignant")

    members = db.query(ClassMembership).filter(
        ClassMembership.class_id == class_id,
        ClassMembership.academic_year_id == cls.academic_year_id,
        ClassMembership.left_at.is_(None),
    ).all()
    student_ids = {m.student_id for m in members}
    activities = db.query(EvaluationActivity).filter(
        EvaluationActivity.class_id == class_id,
        EvaluationActivity.academic_period_id == academic_period_id,
        EvaluationActivity.is_active.is_(True),
    ).order_by(EvaluationActivity.created_at.desc()).all()
    activity_rows = []
    for activity in activities:
        count = db.query(EvaluationResult).filter(EvaluationResult.activity_id == activity.id).count()
        activity_rows.append({
            "id": activity.id, "name": activity.name, "mode": activity.mode,
            "assessment_type": activity.assessment_type, "max_score": activity.max_score,
            "coefficient": activity.coefficient, "entered": count, "total": len(student_ids),
            "completion_percent": round((count / len(student_ids)) * 100, 1) if student_ids else 100,
        })
    risks = class_risk_snapshot(db, class_id, cls.academic_year_id, academic_period_id)
    return {
        "class": {"id": cls.id, "name": cls.name, "student_count": len(student_ids)},
        "period": {"id": period.id, "name": period.name, "order_index": period.order_index},
        "activities": activity_rows,
        "risk_students": risks,
        "risk_count": sum(1 for r in risks if r["level"] in ("warning", "critical")),
        "critical_count": sum(1 for r in risks if r["level"] == "critical"),
    }


@router.get("/classes/{class_id}/students/{student_id}/risk")
def student_risk_detail(class_id: int, student_id: int, academic_period_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    from app.models.students import SchoolClass, ClassMembership
    from app.services.pedagogy_engine import student_risk
    cls = db.get(SchoolClass, class_id)
    if not cls:
        raise HTTPException(404, "Classe introuvable")
    school_guard(current_user, cls.school_id)
    member = db.query(ClassMembership).filter(
        ClassMembership.class_id == class_id,
        ClassMembership.student_id == student_id,
        ClassMembership.academic_year_id == cls.academic_year_id,
        ClassMembership.left_at.is_(None),
    ).first()
    if not member:
        raise HTTPException(404, "Élève non inscrit dans cette classe")
    risk = student_risk(db, student_id, class_id, academic_period_id)
    return {"student_id": student_id, "score": risk.score, "level": risk.level, "reasons": risk.reasons}
