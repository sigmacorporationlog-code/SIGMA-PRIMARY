"""Générateur de matricules SIGMA: configurable, déterministe et concurrent-safe."""
from __future__ import annotations

from sqlalchemy import update
from sqlalchemy.orm import Session

from app.models.organization import School, AcademicYear
from app.models.students import Student, SchoolClass, Level, Stream

DEFAULT_TEMPLATE = "{YY}{SEQ:05}"
STRATEGIES = {
    "sequence": "{SEQ:06}",
    "year_sequence": "{YY}{SEQ:05}",
    "year_level_sequence": "{YY}{LEVEL}{SEQ:04}",
    "school_year_sequence": "{SCHOOL}{YY}{SEQ:04}",
    "custom": DEFAULT_TEMPLATE,
}


def _safe_code(value: str | None, fallback: str = "X") -> str:
    value = "".join(ch for ch in (value or "").upper() if ch.isalnum())
    return value[:12] or fallback


def validate_template(template: str) -> str:
    template = template.strip().upper()
    if not template or len(template) > 80:
        raise ValueError("Le format du matricule est invalide")
    if "{SEQ" not in template:
        raise ValueError("Le format du matricule doit contenir {SEQ}")
    allowed = {"SEQ", "YY", "YYYY", "LEVEL", "STREAM", "SCHOOL", "CAMPUS"}
    import re
    for token in re.findall(r"\{([A-Z]+)(?::\d+)?\}", template):
        if token not in allowed:
            raise ValueError(f"Jeton matricule inconnu: {{{token}}}")
    return template


def _render(template: str, school: School, sequence: int, year: AcademicYear | None, klass: SchoolClass | None, level: Level | None, stream: Stream | None) -> str:
    label = year.label if year else ""
    start = label[:4] if label[:4].isdigit() else ""
    yy = start[-2:] if start else "00"
    values = {
        "YY": yy,
        "YYYY": start or "0000",
        "LEVEL": _safe_code(level.name if level else None),
        "STREAM": _safe_code(stream.name if stream else None),
        "SCHOOL": _safe_code(school.short_name or school.name, "SCH"),
        "CAMPUS": _safe_code(str(klass.campus_id) if klass and klass.campus_id else None, "C"),
    }
    import re
    def repl(match):
        key, width = match.group(1), match.group(2)
        if key == "SEQ":
            return str(sequence).zfill(int(width or 1))
        return values[key]
    result = re.sub(r"\{([A-Z]+)(?::(\d+))?\}", repl, template)
    result = "".join(ch for ch in result if ch.isalnum() or ch in "-_/")
    if not result:
        raise ValueError("Le matricule généré est vide")
    return result[:50]


def next_matricule(db: Session, school_id: int, class_id: int | None = None, academic_year_id: int | None = None) -> str:
    school = db.get(School, school_id)
    if not school:
        raise ValueError("Établissement introuvable")
    strategy = getattr(school, "matricule_strategy", "year_sequence") or "year_sequence"
    template = getattr(school, "matricule_template", None) or STRATEGIES.get(strategy, DEFAULT_TEMPLATE)
    template = validate_template(template)
    # UPDATE atomique: fonctionne avec SQLite et PostgreSQL, contrairement à count()+1.
    result = db.execute(
        update(School).where(School.id == school_id).values(matricule_next_sequence=School.matricule_next_sequence + 1)
    )
    if result.rowcount != 1:
        raise ValueError("Impossible d'incrémenter la séquence des matricules")
    db.refresh(school)
    sequence = school.matricule_next_sequence
    year = db.get(AcademicYear, academic_year_id) if academic_year_id else None
    klass = db.get(SchoolClass, class_id) if class_id else None
    level = db.get(Level, klass.level_id) if klass else None
    stream = db.get(Stream, klass.stream_id) if klass and klass.stream_id else None
    candidate = _render(template, school, sequence, year, klass, level, stream)
    # Une contrainte DB reste la barrière finale. En cas de collision historique,
    # on avance la séquence et on recommence plutôt que de retourner un doublon.
    while db.query(Student.id).filter(Student.school_id == school_id, Student.matricule == candidate).first():
        result = db.execute(update(School).where(School.id == school_id).values(matricule_next_sequence=School.matricule_next_sequence + 1))
        if result.rowcount != 1:
            raise ValueError("Impossible d'avancer la séquence des matricules")
        db.refresh(school)
        candidate = _render(template, school, school.matricule_next_sequence, year, klass, level, stream)
    return candidate
