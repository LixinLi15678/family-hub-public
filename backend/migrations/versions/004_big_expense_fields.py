"""add big expense fields to income and expense

Revision ID: 004_big_expense_fields
Revises: 003_trip_status
Create Date: 2025-12-05
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '004_big_expense_fields'
down_revision = '003_trip_status'
branch_labels = None
browse = None
depends_on = None


def upgrade() -> None:
    op.add_column('expense_categories', sa.Column('is_big_expense', sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column('expenses', sa.Column('is_big_expense', sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column('incomes', sa.Column('big_expense_reserved', sa.Numeric(12, 2), nullable=False, server_default='0'))
    op.add_column('incomes', sa.Column('reserve_mode', sa.String(length=10), nullable=True))
    op.add_column('incomes', sa.Column('reserve_value', sa.Numeric(12, 2), nullable=True))

    # Remove server defaults to avoid impacting future writes
    op.alter_column('expense_categories', 'is_big_expense', server_default=None)
    op.alter_column('expenses', 'is_big_expense', server_default=None)
    op.alter_column('incomes', 'big_expense_reserved', server_default=None)


def downgrade() -> None:
    op.drop_column('incomes', 'reserve_value')
    op.drop_column('incomes', 'reserve_mode')
    op.drop_column('incomes', 'big_expense_reserved')
    op.drop_column('expenses', 'is_big_expense')
    op.drop_column('expense_categories', 'is_big_expense')
