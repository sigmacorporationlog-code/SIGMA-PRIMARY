from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator


def _money(value: Decimal) -> Decimal:
    value = Decimal(value).quantize(Decimal("0.01"))
    return value


class FeeStructureCreate(BaseModel):
    school_id: int
    academic_year_id: int
    level_id: int | None = None
    fee_type: str
    label: str
    amount: Decimal = Field(gt=0, max_digits=14, decimal_places=2)

    @field_validator("amount", mode="after")
    @classmethod
    def normalize_amount(cls, value: Decimal) -> Decimal:
        return _money(value)


class InvoiceCreate(BaseModel):
    student_id: int
    academic_year_id: int
    fee_structure_id: int
    amount_due: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    discount_amount: Decimal = Field(default=Decimal("0.00"), ge=0, max_digits=14, decimal_places=2)
    due_date: date | None = None

    @field_validator("amount_due", "discount_amount", mode="after")
    @classmethod
    def normalize_money(cls, value: Decimal) -> Decimal:
        return _money(value)

    @field_validator("discount_amount")
    @classmethod
    def discount_not_exceed_total(cls, value: Decimal, info):
        amount_due = info.data.get("amount_due")
        if amount_due is not None and value > amount_due:
            raise ValueError("La remise ne peut pas dépasser le montant dû")
        return value


class _MoneyOutput(BaseModel):
    model_config = ConfigDict(from_attributes=True, json_encoders={Decimal: float})


class InvoiceOut(_MoneyOutput):
    id: int
    student_id: int
    amount_due: Decimal
    discount_amount: Decimal
    status: str


class PaymentCreate(BaseModel):
    invoice_id: int
    student_id: int
    amount: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    method: str
    paid_at: datetime | None = None
    idempotency_key: str | None = Field(default=None, min_length=16, max_length=100)

    @field_validator("amount", mode="after")
    @classmethod
    def normalize_amount(cls, value: Decimal) -> Decimal:
        return _money(value)


class PaymentOut(_MoneyOutput):
    id: int
    invoice_id: int
    student_id: int
    amount: Decimal
    method: str
    is_cancelled: bool


class ReceiptOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    payment_id: int
    receipt_number: str
    print_count: int


class PaymentCancel(BaseModel):
    reason: str
