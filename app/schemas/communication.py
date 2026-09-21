from pydantic import BaseModel, ConfigDict


class SmsSendToPhone(BaseModel):
    school_id: int
    phone: str
    body: str
    recipient_label: str | None = None
    campaign_label: str | None = None


class SmsSendToClass(BaseModel):
    school_id: int
    class_id: int
    body: str
    campaign_label: str | None = None


class SmsSendToUnpaid(BaseModel):
    school_id: int
    academic_year_id: int
    body: str
    campaign_label: str | None = None


class SmsMessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    recipient_phone: str
    recipient_label: str | None
    body: str
    status: str
    error_message: str | None
    attempts: int


class SmsSendToGuardian(BaseModel):
    school_id: int
    guardian_id: int
    body: str
    campaign_label: str | None = None

class SmsSendToTarget(BaseModel):
    school_id: int
    target_type: str  # class / level / stream / school
    target_id: int | None = None
    body: str
    campaign_label: str | None = None
