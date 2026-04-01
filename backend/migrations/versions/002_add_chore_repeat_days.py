"""Add repeat_days column to chores table"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision: str = '002_add_repeat_days'
down_revision: Union[str, None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add repeat_days column to chores table for weekly recurrence"""
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = [col["name"] for col in inspector.get_columns("chores")]
    if "repeat_days" not in columns:
        op.add_column(
            'chores',
            sa.Column('repeat_days', sa.JSON(), nullable=True)
        )


def downgrade() -> None:
    """Remove repeat_days column from chores table"""
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = [col["name"] for col in inspector.get_columns("chores")]
    if "repeat_days" in columns:
        op.drop_column('chores', 'repeat_days')
