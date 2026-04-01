"""add expense diamond spends table

Revision ID: 007_add_expense_diamond_spends
Revises: 006_add_daily_login_reward_date
Create Date: 2025-12-13
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = "007_add_expense_diamond_spends"
down_revision = "006_add_daily_login_reward_date"
branch_labels = None
browse = None
depends_on = None


def upgrade() -> None:
    # NOTE:
    # This project also creates tables via SQLAlchemy `create_all()` on startup.
    # In production, the backend may start before Alembic runs, so the table can
    # already exist. Make this migration idempotent to avoid failing deployments.
    bind = op.get_bind()
    inspector = inspect(bind)

    if not inspector.has_table("expense_diamond_spends"):
        op.create_table(
            "expense_diamond_spends",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("expense_id", sa.Integer(), sa.ForeignKey("expenses.id"), nullable=False),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("original_amount", sa.Numeric(12, 2), nullable=False),
            sa.Column("original_currency_id", sa.Integer(), sa.ForeignKey("currencies.id"), nullable=False),
            sa.Column("amount_cny", sa.Numeric(12, 2), nullable=False),
            sa.Column("diamonds", sa.Integer(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.UniqueConstraint("expense_id", "user_id", name="uq_expense_diamond_spend"),
        )

    # Ensure indexes exist (safe if table was created by create_all()).
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_expense_diamond_spends_expense_id "
        "ON expense_diamond_spends (expense_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_expense_diamond_spends_user_id "
        "ON expense_diamond_spends (user_id)"
    )


def downgrade() -> None:
    # Best-effort cleanup
    op.execute("DROP INDEX IF EXISTS ix_expense_diamond_spends_user_id")
    op.execute("DROP INDEX IF EXISTS ix_expense_diamond_spends_expense_id")
    op.execute("DROP TABLE IF EXISTS expense_diamond_spends")
