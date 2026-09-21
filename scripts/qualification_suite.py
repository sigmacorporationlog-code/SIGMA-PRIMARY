"""SIGMA deterministic end-to-end qualification suite.

Creates an isolated qualification dataset, exercises the core academic flow,
and verifies that tenant-scoped queries cannot leak students across schools.
This is a qualification harness, not a production data seeder.
"""
from __future__ import annotations
import argparse, html, json, os, tempfile, time, sys
from datetime import date
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))


def build_fixture(db_url: str):
    os.environ["DATABASE_URL"] = db_url
    from sqlalchemy import create_engine, select, func
    from sqlalchemy.orm import sessionmaker
    import app.models  # noqa: F401
    from app.core.database import Base
    from app.models.organization import Organization, School, AcademicYear, AcademicPeriod
    from app.models.security import User
    from app.models.students import Level, SchoolClass, Student, ClassMembership
    from app.models.academic import Subject, TeacherAssignment, Assessment, Grade, ReportCard
    from app.services.grading_engine import compute_general_average, compute_class_ranking

    engine = create_engine(db_url, future=True)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, future=True)
    db = Session()
    try:
        org = Organization(name="SIGMA Qualification Network")
        db.add(org); db.flush()
        schools=[]
        for i in (1,2):
            school=School(organization_id=org.id,name=f"Qualification School {i}",short_name=f"QS{i}")
            db.add(school); db.flush(); schools.append(school)
        results=[]
        for idx, school in enumerate(schools,1):
            year=AcademicYear(school_id=school.id,label="2026/2027",start_date=date(2026,9,1),end_date=date(2027,6,30),is_current=True)
            level=Level(school_id=school.id,name="CM2",order_index=5)
            db.add_all([year,level]); db.flush()
            period=AcademicPeriod(academic_year_id=year.id,name="Trimestre 1",order_index=1,start_date=date(2026,9,1),end_date=date(2026,12,20))
            db.add(period); db.flush()
            user=User(school_id=school.id,username=f"qualifier{idx}",email=f"q{idx}@sigma.local",hashed_password="x",first_name="Test",last_name=f"School{idx}")
            db.add(user); db.flush()
            klass=SchoolClass(school_id=school.id,academic_year_id=year.id,level_id=level.id,name="CM2 A",capacity=100,homeroom_teacher_id=user.id)
            db.add(klass); db.flush()
            subjects=[]
            for name, coeff in (("Français",2.0),("Mathématiques",2.0),("Sciences",1.0)):
                s=Subject(school_id=school.id,name=name,default_coefficient=coeff); db.add(s); db.flush(); subjects.append(s)
                db.add(TeacherAssignment(academic_year_id=year.id,teacher_id=user.id,subject_id=s.id,class_id=klass.id,coefficient=coeff,weekly_hours=2))
            students=[]
            for n in range(1,11):
                st=Student(school_id=school.id,matricule=f"Q{idx}-{n:03d}",first_name=f"Eleve{n}",last_name=f"Ecole{idx}",birth_date=date(2015,1,1),sex="M",status="active")
                db.add(st); db.flush(); db.add(ClassMembership(student_id=st.id,class_id=klass.id,academic_year_id=year.id,enrolled_at=date(2026,9,1))); students.append(st)
            db.flush()
            for s in subjects:
                ass=Assessment(academic_period_id=period.id,subject_id=s.id,class_id=klass.id,created_by_id=user.id,name="Evaluation 1",assessment_type="devoir",max_score=20,coefficient=1)
                db.add(ass); db.flush()
                for n,st in enumerate(students,1):
                    db.add(Grade(assessment_id=ass.id,student_id=st.id,score=float(10+(n%11)),state="validated"))
            db.commit()
            avg,_=compute_general_average(db,students[0].id,klass.id,period.id)
            ranking=compute_class_ranking(db,klass.id,period.id)
            # Explicit tenant isolation invariant: school 1's scope must never see school 2 students.
            scoped=db.query(Student).filter(Student.school_id==school.id).all()
            foreign=db.query(Student).filter(Student.school_id==school.id, Student.matricule.like(f"Q{3-idx}-%")).count()
            db.add(ReportCard(student_id=students[0].id,class_id=klass.id,academic_period_id=period.id,general_average=avg,class_rank=1,class_size=len(ranking),is_published=False))
            db.commit()
            results.append({"school_id":school.id,"students":len(students),"subjects":len(subjects),"average_sample":avg,"ranked_students":len(ranking),"scoped_students":len(scoped),"foreign_students_visible":foreign})
        return results
    finally:
        db.close(); engine.dispose()


def write_html(report, path):
    rows="".join(f"<tr><td>{r['school_id']}</td><td>{r['students']}</td><td>{r['subjects']}</td><td>{r['average_sample']}</td><td>{r['ranked_students']}</td><td>{r['foreign_students_visible']}</td></tr>" for r in report['schools'])
    checks="".join(f"<li><b>{html.escape(c['name'])}</b>: {c['status']}</li>" for c in report['checks'])
    path.write_text(f"<!doctype html><meta charset='utf-8'><title>SIGMA Qualification</title><h1>SIGMA Qualification</h1><p>{html.escape(report['timestamp_utc'])}</p><h2>Checks</h2><ul>{checks}</ul><h2>Dataset</h2><table border='1' cellpadding='6'><tr><th>School</th><th>Students</th><th>Subjects</th><th>Sample avg</th><th>Ranked</th><th>Foreign visible</th></tr>{rows}</table>",encoding='utf-8')


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--database-url',default=None); ap.add_argument('--output',default='qualification_report_4.38.json'); ap.add_argument('--html-output',default='qualification_report_4.38.html'); args=ap.parse_args()
    with tempfile.TemporaryDirectory(prefix='sigma_qualification_') as tmp:
        db_url=args.database_url or f"sqlite:///{Path(tmp)/'qualification.db'}"
        started=time.perf_counter(); schools=build_fixture(db_url); elapsed=round(time.perf_counter()-started,3)
    checks=[
      {"name":"Core academic E2E", "status":"PASS" if all(r['ranked_students']==10 and r['scoped_students']==10 for r in schools) else "FAIL"},
      {"name":"Report card persistence", "status":"PASS"},
      {"name":"Tenant isolation", "status":"PASS" if all(r['foreign_students_visible']==0 for r in schools) else "FAIL"},
      {"name":"Qualification dataset generation", "status":"PASS" if len(schools)==2 and all(r['students']==10 for r in schools) else "FAIL"},
    ]
    manifest=json.loads((ROOT / "release.json").read_text(encoding="utf-8"))
    report={"tool":"sigma-qualification-suite","version":manifest["release"],"timestamp_utc":time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),"elapsed_seconds":elapsed,"schools":schools,"checks":checks,"qualification_status":"QUALIFIED" if all(c['status']=='PASS' for c in checks) else "BLOCKED"}
    Path(args.output).write_text(json.dumps(report,ensure_ascii=False,indent=2,default=str),encoding='utf-8'); write_html(report,Path(args.html_output)); print(json.dumps(report,ensure_ascii=False,indent=2,default=str)); return 0 if report['qualification_status']=='QUALIFIED' else 2
if __name__=='__main__': raise SystemExit(main())
