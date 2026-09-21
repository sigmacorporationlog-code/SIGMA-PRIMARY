from pydantic import BaseModel, ConfigDict, Field


class MessageTemplateCreate(BaseModel):
    school_id: int
    name: str
    event_type: str | None = None
    channel: str = "auto"
    subject: str | None = None
    body: str
    variables: list[str] = []


class MessageTemplateOut(MessageTemplateCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    is_active: bool


class MessageSend(BaseModel):
    school_id: int
    guardian_id: int
    body: str
    channel: str = "auto"
    title: str = "Message SIGMA"
    student_id: int | None = None


class MessageDeliveryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    guardian_id: int | None
    student_id: int | None
    channel: str
    status: str
    body: str
    provider_reference: str | None
    error_message: str | None
    attempts: int


class CampaignCreate(BaseModel):
    school_id: int
    name: str
    body: str
    channel: str = "auto"
    target_type: str
    target_id: int | None = None


class CampaignOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    channel: str
    target_type: str
    target_id: int | None
    status: str
    total_recipients: int
    sent_count: int
    failed_count: int
