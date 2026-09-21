from decimal import Decimal
from pydantic import BaseModel, ConfigDict


class SubjectCreate(BaseModel):
    school_id: int
    name: str
    default_coefficient: Decimal = 1.0


class SubjectOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    school_id: int
    name: str
    default_coefficient: float


class TeacherAssignmentCreate(BaseModel):
    academic_year_id: int
    teacher_id: int
    subject_id: int
    class_id: int
    coefficient: Decimal | None = None
    weekly_hours: float | None = None


class AssessmentCreate(BaseModel):
    academic_period_id: int
    subject_id: int
    class_id: int
    name: str
    assessment_type: str
    max_score: Decimal = 20.0
    coefficient: Decimal = 1.0


class AssessmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    academic_period_id: int
    subject_id: int
    class_id: int
    name: str
    assessment_type: str
    max_score: float
    coefficient: float


class GradeUpsert(BaseModel):
    student_id: int
    score: Decimal | None = None
    is_absent: bool = False
    comment: str | None = None


class GradeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    assessment_id: int
    student_id: int
    score: float | None
    is_absent: bool
    state: str


class GradeStateTransition(BaseModel):
    grade_ids: list[int]
    to_state: str


class GeneralAverageOut(BaseModel):
    student_id: int
    class_id: int
    academic_period_id: int
    general_average: float | None
    subjects: list[dict]
