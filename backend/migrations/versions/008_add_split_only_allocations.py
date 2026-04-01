"""add split-only allocation fields to expenses

Revision ID: 008_add_split_only_allocations
Revises: 007_add_expense_diamond_spends
Create Date: 2025-12-13
"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "008_add_split_only_allocations"
down_revision = "007_add_expense_diamond_spends"
branch_labels = None
browse = None
depends_on = None


def upgrade() -> None:
    # Use IF NOT EXISTS to be resilient in environments where schema might
    # have been partially created outside Alembic.
    op.execute("ALTER TABLE expenses ADD COLUMN IF NOT EXISTS allocation_source_id INTEGER")
    op.execute("ALTER TABLE expenses ADD COLUMN IF NOT EXISTS allocation_payer_id INTEGER")
    op.execute("CREATE INDEX IF NOT EXISTS ix_expenses_allocation_source_id ON expenses (allocation_source_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_expenses_allocation_payer_id ON expenses (allocation_payer_id)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_expenses_allocation_payer_id")
    op.execute("DROP INDEX IF EXISTS ix_expenses_allocation_source_id")
    op.execute("ALTER TABLE expenses DROP COLUMN IF EXISTS allocation_payer_id")
    op.execute("ALTER TABLE expenses DROP COLUMN IF EXISTS allocation_source_id")

