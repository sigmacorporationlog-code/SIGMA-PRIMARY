"""SIGMA Connect 3.1.0: campaigns, templates and delivery tracking."""
from alembic import op
import sqlalchemy as sa

revision = "20260914_3100"
down_revision = "20260914_3000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("message_templates",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("school_id", sa.Integer(), sa.ForeignKey("schools.id"), nullable=False),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("event_type", sa.String(100), nullable=True),
        sa.Column("channel", sa.String(30), nullable=False, server_default="auto"),
        sa.Column("subject", sa.String(255), nullable=True),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("variables", sa.JSON(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("school_id", "name", name="uq_message_template_school_name"))
    op.create_index("ix_message_templates_school_id", "message_templates", ["school_id"])
    op.create_index("ix_message_templates_event_type", "message_templates", ["event_type"])

    op.create_table("message_campaigns",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("school_id", sa.Integer(), sa.ForeignKey("schools.id"), nullable=False),
        sa.Column("created_by_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("channel", sa.String(30), nullable=False, server_default="auto"),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("target_type", sa.String(30), nullable=False),
        sa.Column("target_id", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(30), nullable=False, server_default="draft"),
        sa.Column("total_recipients", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("sent_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failed_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_message_campaigns_school_id", "message_campaigns", ["school_id"])

    op.create_table("message_recipients",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("campaign_id", sa.Integer(), sa.ForeignKey("message_campaigns.id", ondelete="CASCADE"), nullable=False),
        sa.Column("guardian_id", sa.Integer(), sa.ForeignKey("guardians.id"), nullable=True),
        sa.Column("student_id", sa.Integer(), sa.ForeignKey("students.id"), nullable=True),
        sa.Column("recipient_phone", sa.String(50), nullable=True),
        sa.Column("recipient_email", sa.String(255), nullable=True),
        sa.Column("recipient_label", sa.String(255), nullable=True),
        sa.Column("status", sa.String(30), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_message_recipients_campaign_id", "message_recipients", ["campaign_id"])
    op.create_index("ix_message_recipients_guardian_id", "message_recipients", ["guardian_id"])
    op.create_index("ix_message_recipients_student_id", "message_recipients", ["student_id"])

    op.create_table("message_deliveries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("school_id", sa.Integer(), sa.ForeignKey("schools.id"), nullable=False),
        sa.Column("campaign_id", sa.Integer(), sa.ForeignKey("message_campaigns.id", ondelete="SET NULL"), nullable=True),
        sa.Column("recipient_id", sa.Integer(), sa.ForeignKey("message_recipients.id", ondelete="SET NULL"), nullable=True),
        sa.Column("guardian_id", sa.Integer(), sa.ForeignKey("guardians.id"), nullable=True),
        sa.Column("student_id", sa.Integer(), sa.ForeignKey("students.id"), nullable=True),
        sa.Column("channel", sa.String(30), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="queued"),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("provider_reference", sa.String(255), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_message_deliveries_school_id", "message_deliveries", ["school_id"])
    op.create_index("ix_message_deliveries_campaign_id", "message_deliveries", ["campaign_id"])
    op.create_index("ix_message_deliveries_guardian_id", "message_deliveries", ["guardian_id"])
    op.create_index("ix_message_deliveries_student_id", "message_deliveries", ["student_id"])
    op.create_index("ix_message_deliveries_status", "message_deliveries", ["status"])

    op.create_table("message_conversations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("school_id", sa.Integer(), sa.ForeignKey("schools.id"), nullable=False),
        sa.Column("guardian_id", sa.Integer(), sa.ForeignKey("guardians.id"), nullable=False),
        sa.Column("subject", sa.String(255), nullable=True),
        sa.Column("status", sa.String(30), nullable=False, server_default="open"),
        sa.Column("last_message_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_message_conversations_school_id", "message_conversations", ["school_id"])
    op.create_index("ix_message_conversations_guardian_id", "message_conversations", ["guardian_id"])

    op.create_table("whatsapp_configurations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("school_id", sa.Integer(), sa.ForeignKey("schools.id"), nullable=False, unique=True),
        sa.Column("provider", sa.String(50), nullable=False, server_default="meta_cloud_api"),
        sa.Column("phone_number_id", sa.String(150), nullable=True),
        sa.Column("business_account_id", sa.String(150), nullable=True),
        sa.Column("access_token", sa.Text(), nullable=True),
        sa.Column("api_base_url", sa.String(255), nullable=False, server_default="https://graph.facebook.com"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("settings", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False))


def downgrade() -> None:
    op.drop_table("whatsapp_configurations")
    op.drop_index("ix_message_conversations_guardian_id", table_name="message_conversations")
    op.drop_index("ix_message_conversations_school_id", table_name="message_conversations")
    op.drop_table("message_conversations")
    op.drop_index("ix_message_deliveries_status", table_name="message_deliveries")
    op.drop_index("ix_message_deliveries_student_id", table_name="message_deliveries")
    op.drop_index("ix_message_deliveries_guardian_id", table_name="message_deliveries")
    op.drop_index("ix_message_deliveries_campaign_id", table_name="message_deliveries")
    op.drop_index("ix_message_deliveries_school_id", table_name="message_deliveries")
    op.drop_table("message_deliveries")
    op.drop_index("ix_message_recipients_student_id", table_name="message_recipients")
    op.drop_index("ix_message_recipients_guardian_id", table_name="message_recipients")
    op.drop_index("ix_message_recipients_campaign_id", table_name="message_recipients")
    op.drop_table("message_recipients")
    op.drop_index("ix_message_campaigns_school_id", table_name="message_campaigns")
    op.drop_table("message_campaigns")
    op.drop_index("ix_message_templates_event_type", table_name="message_templates")
    op.drop_index("ix_message_templates_school_id", table_name="message_templates")
    op.drop_table("message_templates")
