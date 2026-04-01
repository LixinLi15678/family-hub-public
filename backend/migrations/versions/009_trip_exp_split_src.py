"""add trip expense split source expense id

Revision ID: 009_trip_exp_split_src
Revises: 008_add_split_only_allocations
Create Date: 2025-12-15
"""

from alembic import op


# revision identifiers, used by Alembic.
# NOTE: alembic_version.version_num is commonly VARCHAR(32); keep this <= 32 chars.
revision = "009_trip_exp_split_src"
down_revision = "008_add_split_only_allocations"
branch_labels = None
browse = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE trip_expenses ADD COLUMN IF NOT EXISTS split_source_expense_id INTEGER"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_trip_expenses_split_source_expense_id ON trip_expenses (split_source_expense_id)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_trip_expenses_split_source_expense_id")
    op.execute("ALTER TABLE trip_expenses DROP COLUMN IF EXISTS split_source_expense_id")

