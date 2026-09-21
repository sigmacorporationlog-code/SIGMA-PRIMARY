from datetime import date

from pydantic import BaseModel, ConfigDict


class CardTemplateCreate(BaseModel):
    school_id: int
    name: str
    card_type: str = "student_id"
    layout: dict = {}
    is_default: bool = False


class CardTemplateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    school_id: int
    name: str
    card_type: str
    layout: dict
    is_default: bool


class IdCardIssue(BaseModel):
    school_id: int
    template_id: int
    holder_type: str  # student / staff
    student_id: int | None = None
    user_id: int | None = None
    validity_years: int | None = None


class IdCardOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    card_number: str
    holder_type: str
    student_id: int | None
    user_id: int | None
    issued_at: date
    expires_at: date | None
    is_active: bool
    print_count: int
    status: str = "active"


class IdCardRevoke(BaseModel):
    reason: str


class IdCardLifecycleUpdate(BaseModel):
    status: str
    note: str | None = None


class IdCardBulkIssue(BaseModel):
    school_id: int
    template_id: int
    class_id: int
    validity_years: int | None = None


class CardMatriculePreview(BaseModel):
    school_id: int
    count: int = 1
    strategy: str = "year_sequence"
