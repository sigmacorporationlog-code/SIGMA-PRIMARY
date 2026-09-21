from decimal import Decimal
from pydantic import BaseModel, ConfigDict, field_validator

class FrameworkCreate(BaseModel):
    school_id: int
    school_year_id: int
    section: str
    cycle: str
    name: str
    version: str = "2018"
    active: bool = True
    gpa_mode: str = "overall_scale"

    @field_validator("gpa_mode")
    @classmethod
    def validate_gpa_mode(cls, value: str) -> str:
        if value not in {"overall_scale", "subject_weighted"}:
            raise ValueError("gpa_mode doit être 'overall_scale' ou 'subject_weighted'")
        return value

class DomainCreate(BaseModel):
    framework_id: int
    code: str
    name: str
    weight: Decimal | None = None
    display_order: int = 1
    description: str | None = None

class CompetencyCreate(BaseModel):
    domain_id: int
    code: str
    name: str
    description: str | None = None
    display_order: int = 1

class CriterionCreate(BaseModel):
    competency_id: int
    code: str
    label: str
    description: str | None = None
    evaluation_mode: str = "observation"
    max_score: Decimal | None = None
    weight: Decimal | None = None
    display_order: int = 1

class ScaleCreate(BaseModel):
    framework_id: int
    code: str
    label: str
    min_percent: Decimal | None = None
    max_percent: Decimal | None = None
    description: str | None = None
    color: str | None = None
    grade_point: Decimal | None = None
    display_order: int = 1

class ActivityCreate(BaseModel):
    academic_period_id: int
    class_id: int
    subject_id: int | None = None
    criterion_id: int | None = None
    name: str
    assessment_type: str = "formative"
    mode: str = "observation"
    max_score: Decimal | None = None
    coefficient: Decimal = 1.0
    notes: str | None = None

class ResultUpsert(BaseModel):
    student_id: int
    score: Decimal | None = None
    max_score: Decimal | None = None
    is_absent: bool = False
    observation: str | None = None
    strengths: str | None = None
    needs_support: str | None = None

class ConfigOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

class ConfigPatch(BaseModel):
    name: str | None = None
    label: str | None = None
    description: str | None = None
    weight: Decimal | None = None
    display_order: int | None = None
    evaluation_mode: str | None = None
    max_score: Decimal | None = None
    color: str | None = None
    grade_point: Decimal | None = None
    active: bool | None = None
    version: str | None = None
    gpa_mode: str | None = None

    @field_validator("gpa_mode")
    @classmethod
    def validate_gpa_mode(cls, value: str | None) -> str | None:
        if value is not None and value not in {"overall_scale", "subject_weighted"}:
            raise ValueError("gpa_mode doit être 'overall_scale' ou 'subject_weighted'")
        return value


class AppreciationRuleCreate(BaseModel):
    framework_id: int
    code: str
    min_percent: Decimal | None = None
    max_percent: Decimal | None = None
    text_fr: str
    text_en: str
    priority: int = 1
    active: bool = True

class ResultStateTransition(BaseModel):
    result_ids: list[int]
    to_state: str


class PeriodFinalizeRequest(BaseModel):
    framework_id: int
    publish_bulletins: bool = False
    calculate_rank: bool = True

class PeriodPublishRequest(BaseModel):
    publish: bool = True
