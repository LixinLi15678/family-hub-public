"""Add daily exchange rate table

Revision ID: 010_add_exchange_rate_daily
Revises: 009_trip_exp_split_src
Create Date: 2025-02-20 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = "010_add_exchange_rate_daily"
down_revision = "009_trip_exp_split_src"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if "exchange_rate_daily" in inspector.get_table_names():
        return

    op.create_table(
        "exchange_rate_daily",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("rate_date", sa.Date(), nullable=False),
        sa.Column("from_currency_id", sa.Integer(), sa.ForeignKey("currencies.id"), nullable=False),
        sa.Column("to_currency_id", sa.Integer(), sa.ForeignKey("currencies.id"), nullable=False),
        sa.Column("rate", sa.Numeric(12, 6), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint(
            "rate_date",
            "from_currency_id",
            "to_currency_id",
            name="uq_exchange_rate_daily",
        ),
    )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if "exchange_rate_daily" not in inspector.get_table_names():
        return
    op.drop_table("exchange_rate_daily")
