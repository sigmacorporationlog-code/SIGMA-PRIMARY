from datetime import datetime
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base
from app.models.mixins import TimestampMixin


class PaymentGatewayEvent(Base, TimestampMixin):
    """Inbox idempotente des événements de paiement entrants."""
    __tablename__ = "payment_gateway_events"
    __table_args__ = (
        UniqueConstraint("provider", "external_event_id", name="uq_payment_gateway_event_provider_external"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    provider: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    external_event_id: Mapped[str] = mapped_column(String(180), nullable=False)
    event_type: Mapped[str] = mapped_column(String(60), nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="received", nullable=False)
    # received / processed / ignored / failed
    invoice_id: Mapped[int | None] = mapped_column(ForeignKey("subscription_invoices.id"), nullable=True, index=True)
    amount_xaf: Mapped[int | None] = mapped_column(Integer, nullable=True)
    provider_reference: Mapped[str | None] = mapped_column(String(180), nullable=True)
    signature_valid: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    payload_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
