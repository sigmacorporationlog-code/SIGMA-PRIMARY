"""SIGMA V4.22 — Signed payment gateway webhook inbox."""
from alembic import op
import sqlalchemy as sa

revision = "20260915_5100"
down_revision = "20260915_5000"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "payment_gateway_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("provider", sa.String(40), nullable=False),
        sa.Column("external_event_id", sa.String(180), nullable=False),
        sa.Column("event_type", sa.String(60), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="received"),
        sa.Column("invoice_id", sa.Integer(), sa.ForeignKey("subscription_invoices.id"), nullable=True),
        sa.Column("amount_xaf", sa.Integer(), nullable=True),
        sa.Column("provider_reference", sa.String(180), nullable=True),
        sa.Column("signature_valid", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("payload_json", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True)),
        sa.Column("updated_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("provider", "external_event_id", name="uq_payment_gateway_event_provider_external"),
    )
    op.create_index("ix_payment_gateway_events_provider", "payment_gateway_events", ["provider"])
    op.create_index("ix_payment_gateway_events_invoice_id", "payment_gateway_events", ["invoice_id"])


def downgrade():
    op.drop_table("payment_gateway_events")
