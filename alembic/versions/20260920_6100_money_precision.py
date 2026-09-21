"""SIGMA V4.46.0 H2 — exact monetary values and payment idempotency."""
from alembic import op
import sqlalchemy as sa

revision = "20260920_6100"
down_revision = "20260920_6000"
branch_labels = None
depends_on = None

MONEY_COLUMNS = {
    "fee_structures": ["amount"],
    "invoices": ["amount_due", "discount_amount"],
    "payments": ["amount"],
    "expenses": ["amount"],
    "cash_register_closures": ["total_receipts", "total_expenses", "net_balance"],
    "payment_transactions": ["amount"],
}


def upgrade():
    money_type = sa.Numeric(14, 2)
    bind = op.get_bind()
    dialect = bind.dialect.name
    for table, columns in MONEY_COLUMNS.items():
        if dialect == "postgresql":
            for column in columns:
                op.alter_column(
                    table, column, type_=money_type, existing_type=sa.Float(),
                    postgresql_using=f"ROUND(CAST({column} AS numeric), 2)"
                )
        else:
            # SQLite's batch mode rebuilds the table while preserving data.
            with op.batch_alter_table(table) as batch:
                for column in columns:
                    batch.alter_column(column, type_=money_type, existing_type=sa.Float())

    op.add_column("payments", sa.Column("idempotency_key", sa.String(length=100), nullable=True))
    op.create_index("ix_payments_idempotency_key", "payments", ["idempotency_key"], unique=True)


def downgrade():
    op.drop_index("ix_payments_idempotency_key", table_name="payments")
    op.drop_column("payments", "idempotency_key")
    for table, columns in reversed(list(MONEY_COLUMNS.items())):
        with op.batch_alter_table(table) as batch:
            for column in columns:
                batch.alter_column(column, type_=sa.Float(), existing_type=sa.Numeric(14, 2))
