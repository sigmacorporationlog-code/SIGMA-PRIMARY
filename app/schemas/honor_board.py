from pydantic import BaseModel, ConfigDict, Field, model_validator


class HonorBoardRuleCreate(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    criteria: dict = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_criteria(self):
        criteria = self.criteria or {}
        if "min_average" in criteria:
            value = float(criteria["min_average"])
            if not 0 <= value <= 20:
                raise ValueError("min_average doit être compris entre 0 et 20")
        if "max_unjustified_absences" in criteria:
            value = int(criteria["max_unjustified_absences"])
            if value < 0:
                raise ValueError("max_unjustified_absences doit être positif ou nul")
        if "min_subject_average" in criteria:
            value = float(criteria["min_subject_average"])
            if not 0 <= value <= 20:
                raise ValueError("min_subject_average doit être compris entre 0 et 20")
        if "exclude_statuses" in criteria:
            if not isinstance(criteria["exclude_statuses"], list):
                raise ValueError("exclude_statuses doit être une liste")
        return self


class HonorBoardRuleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    school_id: int
    name: str
    criteria: dict


class HonorBoardGenerateRequest(BaseModel):
    academic_period_id: int
    class_id: int | None = None
    level_id: int | None = None
    stream_id: int | None = None
    preview: bool = False


class HonorBoardEntryOut(BaseModel):
    id: int | None
    rule_id: int
    student_id: int
    student_name: str
    matricule: str
    class_id: int | None
    class_name: str
    academic_period_id: int
    score: float
    rank: int
    is_validated: bool
    unjustified_absences: int


class HonorBoardPreviewOut(BaseModel):
    rule_id: int
    rule_name: str
    academic_period_id: int
    class_ids: list[int]
    generated_count: int
    entries: list[dict]
