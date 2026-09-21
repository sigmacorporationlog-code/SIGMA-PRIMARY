from datetime import date

from pydantic import BaseModel, ConfigDict, field_validator

from app.services.phone import normalize_international_phone


class StudentCreate(BaseModel):
    school_id: int
    matricule: str | None = None
    first_name: str
    last_name: str
    birth_date: date | None = None
    birth_place: str | None = None
    sex: str | None = None
    nationality: str | None = None
    address: str | None = None
    guardian_first_name: str | None = None
    guardian_last_name: str | None = None
    guardian_relationship: str | None = None
    guardian_phone: str | None = None
    guardian_email: str | None = None
    guardian_address: str | None = None
    class_id: int | None = None
    academic_year_id: int | None = None

    @field_validator("guardian_phone")
    @classmethod
    def _validate_guardian_phone(cls, v):
        return normalize_international_phone(v)


class StudentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    school_id: int
    matricule: str
    first_name: str
    last_name: str
    birth_date: date | None
    sex: str | None
    status: str
    is_active: bool


class SchoolClassCreate(BaseModel):
    school_id: int
    academic_year_id: int
    level_id: int
    stream_id: int | None = None
    campus_id: int | None = None
    name: str
    homeroom_teacher_id: int | None = None
    capacity: int | None = None


class SchoolClassUpdate(BaseModel):
    academic_year_id: int | None = None
    level_id: int | None = None
    stream_id: int | None = None
    campus_id: int | None = None
    name: str | None = None
    homeroom_teacher_id: int | None = None
    capacity: int | None = None


class LevelUpdate(BaseModel):
    name: str | None = None
    order_index: int | None = None


class StreamUpdate(BaseModel):
    name: str | None = None


class SchoolClassOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    school_id: int
    academic_year_id: int
    level_id: int
    stream_id: int | None
    name: str
    is_active: bool


class ClassMembershipCreate(BaseModel):
    student_id: int
    class_id: int
    academic_year_id: int
    enrolled_at: date
    enrollment_type: str = "inscription"


class GuardianCreate(BaseModel):
    school_id: int
    first_name: str
    last_name: str
    relationship_type: str
    phone: str | None = None
    email: str | None = None
    address: str | None = None
    can_pick_up_child: bool = False

    @field_validator("phone")
    @classmethod
    def _validate_phone(cls, v):
        return normalize_international_phone(v)


class StudentGuardianLink(BaseModel):
    student_id: int
    guardian_id: int
    is_primary_contact: bool = False


class GuardianOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    school_id: int
    first_name: str
    last_name: str
    relationship_type: str
    phone: str | None
    email: str | None
    address: str | None
    can_pick_up_child: bool


class EnrollmentCreate(BaseModel):
    student_id: int
    class_id: int
    academic_year_id: int
    enrolled_at: date
    enrollment_type: str = "inscription"


class EnrollmentTransfer(BaseModel):
    student_id: int
    target_class_id: int
    academic_year_id: int
    effective_date: date
    reason: str | None = None


class GuardianUpdate(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    relationship_type: str | None = None
    phone: str | None = None
    email: str | None = None
    address: str | None = None

    @field_validator("phone")
    @classmethod
    def _validate_phone(cls, v):
        return normalize_international_phone(v)
    can_pick_up_child: bool | None = None
