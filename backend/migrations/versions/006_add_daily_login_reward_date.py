"""add daily login reward tracking field

Revision ID: 006_add_daily_login_reward_date
Revises: 005_add_split_only_expense_flag
Create Date: 2025-12-13
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '006_add_daily_login_reward_date'
down_revision = '005_add_split_only_expense_flag'
branch_labels = None
browse = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'users',
        sa.Column('last_daily_login_reward_date', sa.String(length=10), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('users', 'last_daily_login_reward_date')

