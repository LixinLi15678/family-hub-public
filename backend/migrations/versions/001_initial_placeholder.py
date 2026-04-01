"""Initial baseline placeholder

Revision ID: 001
Revises: 
Create Date: 2024-01-01 00:00:00.000000

This placeholder marks the existing schema as baseline so later revisions can apply.
"""
from typing import Sequence, Union
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Baseline placeholder - no schema changes
    pass


def downgrade() -> None:
    # Baseline placeholder - nothing to revert
    pass
