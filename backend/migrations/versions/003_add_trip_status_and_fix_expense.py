"""Add trip status field and fix trip expense currency_id

Revision ID: 003
Revises: 002
Create Date: 2024-01-15 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
# Keep the original revision id for Alembic history
revision: str = '003_trip_status'
down_revision: Union[str, None] = '002_add_repeat_days'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Add status field to trips table
    Change trip_expenses.currency_id to nullable
    """
    bind = op.get_bind()
    inspector = inspect(bind)
    
    # Add status column to trips
    trip_cols = [col["name"] for col in inspector.get_columns("trips")]
    if "status" not in trip_cols:
        op.add_column(
            'trips',
            sa.Column('status', sa.String(20), nullable=False, server_default='planned')
        )
    
    # Make currency_id nullable in trip_expenses
    expense_cols = inspector.get_columns("trip_expenses")
    for col in expense_cols:
        if col["name"] == "currency_id":
            if not col.get("nullable", False):
                op.alter_column(
                    'trip_expenses',
                    'currency_id',
                    existing_type=sa.Integer(),
                    nullable=True
                )
            break


def downgrade() -> None:
    """Remove status field from trips table"""
    bind = op.get_bind()
    inspector = inspect(bind)
    trip_cols = [col["name"] for col in inspector.get_columns("trips")]
    if "status" in trip_cols:
        op.drop_column('trips', 'status')
    
    # Revert currency_id to not nullable (may fail if null values exist)
    expense_cols = inspector.get_columns("trip_expenses")
    for col in expense_cols:
        if col["name"] == "currency_id":
            if col.get("nullable", True):
                op.alter_column(
                    'trip_expenses',
                    'currency_id',
                    existing_type=sa.Integer(),
                    nullable=False
                )
            break
