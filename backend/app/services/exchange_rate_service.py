"""
Exchange rate helpers with daily (historical) support.
"""

from __future__ import annotations

from datetime import date
from typing import Iterable, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.currency import Currency, ExchangeRate, ExchangeRateDaily
from app.utils.currency import (
    fetch_exchange_rates,
    fetch_exchange_rates_for_date,
    get_default_rates,
)


async def get_usd_rate_map_for_date(
    db: AsyncSession,
    rate_date: date,
    currency_ids: Optional[Iterable[int]] = None,
    cache: Optional[dict[date, dict[int, float]]] = None,
) -> dict[int, float]:
    """
    Return USD-based rates for a date as currency_id -> rate.
    For today or on errors, fall back to latest (realtime) rates.
    """
    if cache is not None and rate_date in cache:
        rates_by_id = cache[rate_date]
    else:
        code_to_id, _ = await _load_currency_maps(db)
        usd_id = code_to_id.get("USD")
        today = date.today()

        if rate_date == today:
            rates_by_id = await _get_latest_usd_rates(db, code_to_id, usd_id)
        else:
            rates_by_id = await _get_daily_usd_rates(db, rate_date, code_to_id, usd_id)
            if not rates_by_id:
                rates_by_id = await _get_latest_usd_rates(db, code_to_id, usd_id)

        # Ensure USD rate is always present when possible
        if usd_id and usd_id not in rates_by_id:
            rates_by_id[usd_id] = 1.0

        if cache is not None:
            cache[rate_date] = rates_by_id

    if not currency_ids:
        return rates_by_id

    return {int(cid): float(rates_by_id.get(int(cid), 0)) for cid in currency_ids}


async def convert_to_usd(
    db: AsyncSession,
    amount: float,
    currency_id: int,
    rate_date: date,
    cache: Optional[dict[date, dict[int, float]]] = None,
) -> float:
    """Convert amount in currency_id to USD using date-based rates."""
    rate_map = await get_usd_rate_map_for_date(
        db, rate_date, currency_ids=[currency_id], cache=cache
    )
    rate = float(rate_map.get(int(currency_id), 0) or 0)
    if rate <= 0:
        today_rates = await get_usd_rate_map_for_date(
            db, date.today(), currency_ids=[currency_id], cache=cache
        )
        rate = float(today_rates.get(int(currency_id), 0) or 0)
    if rate <= 0:
        return float(amount)
    return float(amount) / rate


async def _load_currency_maps(db: AsyncSession) -> tuple[dict[str, int], dict[int, str]]:
    result = await db.execute(select(Currency))
    currencies = result.scalars().all()
    code_to_id = {str(c.code): int(c.id) for c in currencies}
    id_to_code = {int(c.id): str(c.code) for c in currencies}
    return code_to_id, id_to_code


async def _get_latest_usd_rates(
    db: AsyncSession,
    code_to_id: dict[str, int],
    usd_id: Optional[int],
) -> dict[int, float]:
    rates_by_id: dict[int, float] = {}
    if usd_id:
        rates_by_id[usd_id] = 1.0

    if usd_id:
        result = await db.execute(
            select(ExchangeRate.to_currency_id, ExchangeRate.rate).where(
                ExchangeRate.from_currency_id == usd_id
            )
        )
        for to_id, rate in result.all():
            rates_by_id[int(to_id)] = float(rate)

    if len(rates_by_id) > 1:
        return rates_by_id

    fetched = await fetch_exchange_rates("USD")
    if fetched:
        for code, rate in fetched.items():
            to_id = code_to_id.get(code)
            if not to_id:
                continue
            rates_by_id[int(to_id)] = float(rate)

    if rates_by_id:
        return rates_by_id

    defaults = get_default_rates()
    for code, rate in defaults.items():
        to_id = code_to_id.get(code)
        if to_id:
            rates_by_id[int(to_id)] = float(rate)

    return rates_by_id


async def _get_daily_usd_rates(
    db: AsyncSession,
    rate_date: date,
    code_to_id: dict[str, int],
    usd_id: Optional[int],
) -> dict[int, float]:
    if not usd_id:
        return {}

    result = await db.execute(
        select(ExchangeRateDaily.to_currency_id, ExchangeRateDaily.rate).where(
            ExchangeRateDaily.rate_date == rate_date,
            ExchangeRateDaily.from_currency_id == usd_id,
        )
    )
    rates_by_id = {int(to_id): float(rate) for to_id, rate in result.all()}

    if rates_by_id:
        return rates_by_id

    fetched = await fetch_exchange_rates_for_date(rate_date, "USD")
    if not fetched:
        return {}

    existing_ids = set(rates_by_id.keys())
    for code, rate in fetched.items():
        to_id = code_to_id.get(code)
        if not to_id or to_id == usd_id:
            continue
        if to_id in existing_ids:
            continue
        db.add(
            ExchangeRateDaily(
                rate_date=rate_date,
                from_currency_id=usd_id,
                to_currency_id=to_id,
                rate=float(rate),
            )
        )
        rates_by_id[int(to_id)] = float(rate)

    await db.flush()
    return rates_by_id
