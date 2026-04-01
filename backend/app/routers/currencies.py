"""
Currency and exchange rate routes
"""
from typing import List
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.currency import Currency, ExchangeRate
from app.services.exchange_rate_service import get_usd_rate_map_for_date
from app.schemas.currency import CurrencyResponse, ExchangeRateResponse
from app.schemas.common import SuccessResponse
from app.utils.security import get_current_user
from app.utils.currency import fetch_exchange_rates, get_default_rates
from pydantic import BaseModel

router = APIRouter(prefix="/currencies", tags=["Currencies"])


class DailyRateBulkRequest(BaseModel):
    dates: List[date]


@router.get("", response_model=SuccessResponse[List[CurrencyResponse]])
async def get_currencies(db: AsyncSession = Depends(get_db)):
    """Get all supported currencies"""
    result = await db.execute(select(Currency))
    currencies = result.scalars().all()
    
    return SuccessResponse(
        data=[CurrencyResponse.model_validate(c) for c in currencies],
        message="获取成功"
    )


@router.get("/exchange-rates", response_model=SuccessResponse[List[ExchangeRateResponse]])
async def get_exchange_rates(db: AsyncSession = Depends(get_db)):
    """Get all exchange rates"""
    result = await db.execute(
        select(ExchangeRate, Currency)
        .join(Currency, ExchangeRate.from_currency_id == Currency.id)
    )
    
    rates = []
    for row in result.all():
        rate = row[0]
        from_currency = row[1]
        
        # Get to_currency
        to_result = await db.execute(
            select(Currency).where(Currency.id == rate.to_currency_id)
        )
        to_currency = to_result.scalar_one()
        
        rates.append(ExchangeRateResponse(
            id=rate.id,
            from_currency_id=rate.from_currency_id,
            to_currency_id=rate.to_currency_id,
            from_currency_code=from_currency.code,
            to_currency_code=to_currency.code,
            rate=float(rate.rate),
            updated_at=rate.updated_at
        ))
    
    return SuccessResponse(data=rates, message="获取成功")


@router.get("/exchange-rates/daily", response_model=SuccessResponse[dict])
async def get_daily_exchange_rates(
    rate_date: date = Query(..., alias="date"),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get USD-based exchange rates for a specific date"""
    result = await db.execute(select(Currency))
    currencies = result.scalars().all()
    id_to_code = {int(c.id): str(c.code) for c in currencies}

    rate_map = await get_usd_rate_map_for_date(db, rate_date)
    rates = {id_to_code[cid]: rate for cid, rate in rate_map.items() if cid in id_to_code}

    return SuccessResponse(
        data={"date": rate_date.isoformat(), "base": "USD", "rates": rates},
        message="获取成功"
    )


@router.post("/exchange-rates/daily/bulk", response_model=SuccessResponse[dict])
async def get_daily_exchange_rates_bulk(
    payload: DailyRateBulkRequest,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get USD-based exchange rates for multiple dates"""
    dates = list({d for d in payload.dates})
    if not dates:
        return SuccessResponse(data={"base": "USD", "rates_by_date": {}}, message="获取成功")

    result = await db.execute(select(Currency))
    currencies = result.scalars().all()
    id_to_code = {int(c.id): str(c.code) for c in currencies}

    cache: dict[date, dict[int, float]] = {}
    rates_by_date: dict[str, dict[str, float]] = {}
    for rate_date in dates:
        rate_map = await get_usd_rate_map_for_date(db, rate_date, cache=cache)
        rates_by_date[rate_date.isoformat()] = {
            id_to_code[cid]: rate for cid, rate in rate_map.items() if cid in id_to_code
        }

    return SuccessResponse(
        data={"base": "USD", "rates_by_date": rates_by_date},
        message="获取成功"
    )


@router.post("/exchange-rates/refresh", response_model=SuccessResponse[dict])
async def refresh_exchange_rates(
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Manually refresh exchange rates from external API"""
    # Fetch latest rates
    rates = await fetch_exchange_rates("USD")
    
    if not rates:
        # Use default rates as fallback
        rates = get_default_rates()
    
    # Get all currencies
    result = await db.execute(select(Currency))
    currencies = {c.code: c.id for c in result.scalars().all()}
    
    updated_count = 0
    
    # Update or create exchange rates (USD to other currencies)
    usd_id = currencies.get("USD")
    if not usd_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="USD currency not found in database"
        )
    
    for code, rate in rates.items():
        if code not in currencies or code == "USD":
            continue
        
        to_id = currencies[code]
        
        # Check if rate exists
        result = await db.execute(
            select(ExchangeRate).where(
                ExchangeRate.from_currency_id == usd_id,
                ExchangeRate.to_currency_id == to_id
            )
        )
        existing = result.scalar_one_or_none()
        
        if existing:
            existing.rate = rate
        else:
            new_rate = ExchangeRate(
                from_currency_id=usd_id,
                to_currency_id=to_id,
                rate=rate
            )
            db.add(new_rate)
        
        updated_count += 1
    
    await db.flush()
    
    return SuccessResponse(
        data={"updated_count": updated_count},
        message=f"已更新 {updated_count} 个汇率"
    )
