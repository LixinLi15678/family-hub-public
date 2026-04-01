"""add split_only flag to expenses

Revision ID: 005_add_split_only_expense_flag
Revises: 004_big_expense_fields
Create Date: 2025-12-12
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '005_add_split_only_expense_flag'
down_revision = '004_big_expense_fields'
branch_labels = None
browse = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'expenses',
        sa.Column('split_only', sa.Boolean(), nullable=False, server_default=sa.false())
    )
    op.alter_column('expenses', 'split_only', server_default=None)


def downgrade() -> None:
    op.drop_column('expenses', 'split_only')

