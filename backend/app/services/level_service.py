"""
Level progression services (diamond spend derived from ledger expenses)
"""

from __future__ import annotations

import math

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.currency import Currency
from app.models.expense import Expense, ExpenseDiamondSpend
from app.services.exchange_rate_service import get_usd_rate_map_for_date
from app.utils.currency import convert_amount, get_default_rates


async def rebuild_expense_diamond_spends(db: AsyncSession, expense: Expense) -> None:
    """
    Rebuild expense-derived diamond spends for a single expense.

    Rules:
    - Only apply to normal expenses (`split_only == False`).
    - If splits exist, allocate by split users (not payer).
    - Otherwise allocate to payer.
    - Convert to CNY using USD-based exchange rates, then diamonds = round(CNY * 10).
    """
    await db.execute(
        delete(ExpenseDiamondSpend).where(ExpenseDiamondSpend.expense_id == expense.id)
    )

    if getattr(expense, "split_only", False):
        return

    # Build per-user allocations (may need to merge duplicate split users).
    #
    # IMPORTANT (async SQLAlchemy): accessing relationship attributes that are not
    # already loaded will trigger lazy IO and can raise MissingGreenlet.
    # Only use `expense.splits` when it's already present on the instance.
    allocations_by_user: dict[int, float] = {}
    splits = []
    if "splits" in getattr(expense, "__dict__", {}):
        splits = list(getattr(expense, "splits", []) or [])
    if splits:
        for split in splits:
            user_id = int(split.user_id)
            share_amount = float(split.share_amount or 0)
            if share_amount <= 0:
                continue
            allocations_by_user[user_id] = allocations_by_user.get(user_id, 0.0) + share_amount
    else:
        allocations_by_user[int(expense.user_id)] = float(expense.amount or 0)

    from_rate, cny_rate = await _get_usd_based_rates(db, int(expense.currency_id), expense.expense_date)
    # Guard against bad/zero rates to avoid 500s on conversion.
    if not (isinstance(from_rate, (int, float)) and math.isfinite(from_rate) and from_rate > 0):
        from_rate = 1.0
    if not (isinstance(cny_rate, (int, float)) and math.isfinite(cny_rate) and cny_rate > 0):
        cny_rate = 7.2

    for user_id, original_amount in allocations_by_user.items():
        cny_amount = convert_amount(original_amount, from_rate, cny_rate)
        diamonds = max(0, int(round(cny_amount * 10)))
        db.add(
            ExpenseDiamondSpend(
                expense_id=int(expense.id),
                user_id=user_id,
                original_amount=round(float(original_amount), 2),
                original_currency_id=int(expense.currency_id),
                amount_cny=round(float(cny_amount), 2),
                diamonds=diamonds,
            )
        )

    await db.flush()


async def delete_expense_diamond_spends(db: AsyncSession, expense_id: int) -> None:
    """Delete all expense-derived diamond spends for a single expense."""
    await db.execute(
        delete(ExpenseDiamondSpend).where(ExpenseDiamondSpend.expense_id == expense_id)
    )


async def _get_usd_based_rates(
    db: AsyncSession,
    from_currency_id: int,
    rate_date,
) -> tuple[float, float]:
    """
    Return (from_rate, cny_rate) where each is the USD->currency rate.
    Fallback to built-in default rates if missing from DB.
    """
    result = await db.execute(
        select(Currency).where(
            (Currency.id == from_currency_id) | (Currency.code.in_(["USD", "CNY"]))
        )
    )
    currencies = result.scalars().all()
    id_to_code = {int(c.id): c.code for c in currencies}
    code_to_id = {c.code: int(c.id) for c in currencies}

    from_code = id_to_code.get(from_currency_id)
    usd_id = code_to_id.get("USD")
    cny_id = code_to_id.get("CNY")

    defaults = get_default_rates()

    # If we can't resolve currency codes, fall back to sane defaults.
    if not from_code:
        return 1.0, float(defaults.get("CNY", 7.2))

    if not usd_id or not cny_id:
        return float(defaults.get(from_code, 1.0)), float(defaults.get("CNY", 7.2))

    rate_ids = []
    if from_currency_id:
        rate_ids.append(from_currency_id)
    if cny_id:
        rate_ids.append(cny_id)

    rate_map = await get_usd_rate_map_for_date(
        db, rate_date, currency_ids=rate_ids
    )

    from_rate = 1.0 if from_currency_id == usd_id else rate_map.get(from_currency_id)
    cny_rate = 1.0 if cny_id == usd_id else rate_map.get(cny_id)

    if from_rate is None:
        from_rate = float(defaults.get(from_code, 1.0))
    if cny_rate is None:
        cny_rate = float(defaults.get("CNY", 7.2))

    from_rate = float(from_rate)
    cny_rate = float(cny_rate)

    # Final hardening: avoid propagating invalid/zero rates to conversion.
    if not (math.isfinite(from_rate) and from_rate > 0):
        from_rate = float(defaults.get(from_code, 1.0))
    if not (math.isfinite(cny_rate) and cny_rate > 0):
        cny_rate = float(defaults.get("CNY", 7.2))

    return from_rate, cny_rate
