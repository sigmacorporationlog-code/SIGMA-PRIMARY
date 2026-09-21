from datetime import date
from io import BytesIO
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from PIL import Image

import app.models  # noqa
from app.core.database import Base
from app.models.organization import School, AcademicYear
from app.models.students import Student, Level, Stream, SchoolClass
from app.services.matricule import next_matricule, validate_template
from app.services.media import save_student_photo
from fastapi import UploadFile


def setup_db():
    e = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(e)
    return sessionmaker(bind=e)()


def test_matricule_is_atomic_and_configurable():
    db = setup_db()
    school = School(name="École Test", short_name="ET", currency="XAF", language="fr", matricule_strategy="year_level_sequence", matricule_template="{YY}-{LEVEL}-{SEQ:04}")
    year = AcademicYear(school=school, label="2026/2027", start_date=date(2026,9,1), end_date=date(2027,6,30))
    level = Level(school_id=school.id, name="CP")
    db.add_all([school, year]); db.flush(); level.school_id=school.id; db.add(level); db.flush()
    klass = SchoolClass(school_id=school.id, academic_year_id=year.id, level_id=level.id, name="CP A")
    db.add(klass); db.flush()
    a = next_matricule(db, school.id, klass.id, year.id)
    b = next_matricule(db, school.id, klass.id, year.id)
    assert a == "26-CP-0001"
    assert b == "26-CP-0002"
    db.rollback()


def test_template_requires_sequence():
    try:
        validate_template("{YY}-{LEVEL}")
    except ValueError:
        pass
    else:
        raise AssertionError("template without sequence must be rejected")


def test_photo_is_normalized_to_square_and_pillow_is_required(tmp_path, monkeypatch):
    monkeypatch.setattr("app.core.config.settings.MEDIA_ROOT", str(tmp_path))
    buf = BytesIO()
    Image.new("RGB", (1200, 800), "white").save(buf, "PNG")
    upload = UploadFile(filename="photo.png", file=BytesIO(buf.getvalue()))
    path = save_student_photo(42, upload, buf.getvalue())
    assert path == "students/42.jpg"
    with Image.open(tmp_path / path) as out:
        assert out.size == (600, 600)
        assert out.format == "JPEG"
