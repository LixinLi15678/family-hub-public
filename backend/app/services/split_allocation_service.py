"""
Split-only allocation service.

When an expense is marked `split_only`, it is used for settlement calculations only.
In that case we create derived per-user expenses so that costs are "allocated" to
split participants (and not counted under the payer).
"""

from __future__ import annotations

from datetime import datetime
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.expense import Expense
from app.services.level_service import rebuild_expense_diamond_spends, delete_expense_diamond_spends


async def sync_split_only_allocations(db: AsyncSession, expense_id: int) -> None:
    """
    Ensure derived allocation expenses match a split-only source expense.

    - Deletes any existing derived expenses for this source.
    - Creates one expense per split participant with amount=share_amount.
    - Sets `allocation_source_id` and `allocation_payer_id` on derived expenses.
    """
    result = await db.execute(
        select(Expense)
        .options(selectinload(Expense.splits))
        .where(Expense.id == expense_id)
    )
    expense = result.scalar_one_or_none()
    if not expense:
        return

    # Only generate derived expenses for split-only records
    if not getattr(expense, "split_only", False):
        return

    payer_id = int(expense.user_id)
    splits = list(expense.splits or [])

    # Delete existing derived expenses + their diamond spends
    derived_rows = (
        await db.execute(
            select(Expense.id).where(Expense.allocation_source_id == expense.id)
        )
    ).all()
    derived_ids = [int(r[0]) for r in derived_rows]
    if derived_ids:
        for did in derived_ids:
            await delete_expense_diamond_spends(db, did)
        await db.execute(delete(Expense).where(Expense.id.in_(derived_ids)))
        await db.flush()

    # If there are no splits, we've already cleaned up old derived rows.
    if not splits:
        return

    now = datetime.utcnow()
    for split in splits:
        allocated_user_id = int(split.user_id)
        share_amount = float(split.share_amount)
        if share_amount <= 0:
            continue

        derived = Expense(
            family_id=int(expense.family_id),
            category_id=int(expense.category_id),
            user_id=allocated_user_id,
            allocation_source_id=int(expense.id),
            allocation_payer_id=payer_id,
            amount=round(share_amount, 2),
            currency_id=int(expense.currency_id),
            description=_build_allocation_description(expense.description),
            expense_date=expense.expense_date,
            is_big_expense=bool(expense.is_big_expense),
            split_only=False,
            created_at=now,
            updated_at=now,
        )
        db.add(derived)
        await db.flush()

        # Create diamond spend for derived expense
        await rebuild_expense_diamond_spends(db, derived)

    await db.flush()


async def delete_split_only_allocations(db: AsyncSession, source_expense_id: int) -> None:
    """Delete derived allocation expenses for a split-only source (and their diamond spends)."""
    derived_rows = (
        await db.execute(
            select(Expense.id).where(Expense.allocation_source_id == source_expense_id)
        )
    ).all()
    derived_ids = [int(r[0]) for r in derived_rows]
    if not derived_ids:
        return

    for did in derived_ids:
        await delete_expense_diamond_spends(db, did)

    await db.execute(delete(Expense).where(Expense.id.in_(derived_ids)))
    await db.flush()


def _build_allocation_description(original: str | None) -> str:
    base = (original or "").strip()
    if base:
        return f"{base}（均摊）"
    return "均摊"
