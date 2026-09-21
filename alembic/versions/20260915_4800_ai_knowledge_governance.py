"""SIGMA V4.14 — gouvernance documentaire et retrieval hybride."""
from alembic import op
import sqlalchemy as sa

revision = "20260915_4800"
down_revision = "20260915_4700"
branch_labels = None
depends_on = None

def upgrade():
    with op.batch_alter_table("ai_knowledge_documents") as b:
        b.add_column(sa.Column("folder", sa.String(length=120), nullable=False, server_default="General"))
        b.add_column(sa.Column("tags_json", sa.JSON(), nullable=False, server_default="[]"))
        b.add_column(sa.Column("status", sa.String(length=30), nullable=False, server_default="published"))
        b.add_column(sa.Column("approved_by_user_id", sa.Integer(), nullable=True))
        b.add_column(sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True))
        b.add_column(sa.Column("published_at", sa.DateTime(timezone=True), nullable=True))
        b.add_column(sa.Column("extraction_method", sa.String(length=40), nullable=True))
        b.create_index("ix_ai_knowledge_documents_status", ["status"])
        b.create_foreign_key("fk_ai_knowledge_documents_approved_by_user", "users", ["approved_by_user_id"], ["id"])
    with op.batch_alter_table("ai_knowledge_documents") as b:
        b.alter_column("folder", server_default=None)
        b.alter_column("tags_json", server_default=None)
        b.alter_column("status", server_default=None)

def downgrade():
    with op.batch_alter_table("ai_knowledge_documents") as b:
        b.drop_constraint("fk_ai_knowledge_documents_approved_by_user", type_="foreignkey")
        b.drop_index("ix_ai_knowledge_documents_status")
        for col in ("extraction_method","published_at","approved_at","approved_by_user_id","status","tags_json","folder"):
            b.drop_column(col)
