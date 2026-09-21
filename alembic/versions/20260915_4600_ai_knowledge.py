"""SIGMA V4.12 — base documentaire RAG institutionnelle."""
from alembic import op
import sqlalchemy as sa

revision = "20260915_4600"
down_revision = "20260914_4500"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ai_knowledge_documents",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("school_id", sa.Integer(), sa.ForeignKey("schools.id"), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("document_type", sa.String(60), nullable=False),
        sa.Column("version", sa.String(80), nullable=True),
        sa.Column("source_name", sa.String(255), nullable=True),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("content_length", sa.Integer(), nullable=False),
        sa.Column("chunk_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.UniqueConstraint("school_id", "content_hash", name="uq_ai_knowledge_school_hash"),
    )
    op.create_index("ix_ai_knowledge_documents_school_id", "ai_knowledge_documents", ["school_id"])
    op.create_index("ix_ai_knowledge_documents_content_hash", "ai_knowledge_documents", ["content_hash"])
    op.create_index("ix_ai_knowledge_documents_is_active", "ai_knowledge_documents", ["is_active"])
    op.create_table(
        "ai_knowledge_chunks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("school_id", sa.Integer(), sa.ForeignKey("schools.id"), nullable=False),
        sa.Column("document_id", sa.Integer(), sa.ForeignKey("ai_knowledge_documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("token_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.UniqueConstraint("document_id", "chunk_index", name="uq_ai_knowledge_chunk_index"),
    )
    op.create_index("ix_ai_knowledge_chunks_school_id", "ai_knowledge_chunks", ["school_id"])
    op.create_index("ix_ai_knowledge_chunks_document_id", "ai_knowledge_chunks", ["document_id"])


def downgrade() -> None:
    op.drop_index("ix_ai_knowledge_chunks_document_id", table_name="ai_knowledge_chunks")
    op.drop_index("ix_ai_knowledge_chunks_school_id", table_name="ai_knowledge_chunks")
    op.drop_table("ai_knowledge_chunks")
    op.drop_index("ix_ai_knowledge_documents_is_active", table_name="ai_knowledge_documents")
    op.drop_index("ix_ai_knowledge_documents_content_hash", table_name="ai_knowledge_documents")
    op.drop_index("ix_ai_knowledge_documents_school_id", table_name="ai_knowledge_documents")
    op.drop_table("ai_knowledge_documents")
