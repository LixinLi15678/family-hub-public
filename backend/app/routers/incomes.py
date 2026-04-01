"""
Income routes
"""
from datetime import date
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.models.expense import Income, Expense
from app.models.currency import Currency
from app.services.exchange_rate_service import convert_to_usd
from app.schemas.expense import IncomeCreate, IncomeUpdate, IncomeResponse
from app.schemas.common import SuccessResponse, PaginatedResponse, PaginatedData
from app.utils.security import get_current_user
from app.utils.cache import cache, invalidate_family_expense_cache

router = APIRouter(prefix="/incomes", tags=["Incomes"])


def _calculate_reserved(amount: float, reserve_mode: Optional[str], reserve_value: Optional[float]) -> tuple[float, Optional[str], Optional[float]]:
    """
    根据预留方式计算大额开销预留金额
    """
    mode = reserve_mode or None
    if not mode or mode == "none":
        return 0.0, None, None

    if mode not in ("percent", "fixed"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": "预留方式无效",
                "code": "INVALID_RESERVE_MODE",
                "hint": "预留方式仅支持: none(不预留), percent(按比例), fixed(固定金额)"
            }
        )

    if reserve_value is None or reserve_value < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": "预留值必须提供且不能为负数",
                "code": "INVALID_RESERVE_VALUE",
                "hint": f"当前预留方式为 {mode}，请提供大于等于 0 的预留值"
            }
        )

    if mode == "percent":
        if reserve_value > 100:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "message": f"预留比例 {reserve_value}% 超出范围",
                    "code": "RESERVE_PERCENT_OUT_OF_RANGE",
                    "hint": "预留比例必须在 0-100 之间"
                }
            )
        reserved = amount * reserve_value / 100
    else:
        reserved = reserve_value

    if reserved > amount:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": f"预留金额 {reserved:.2f} 超过收入金额 {amount:.2f}",
                "code": "RESERVE_EXCEEDS_INCOME",
                "hint": "预留金额不能大于收入金额，请调整预留值"
            }
        )

    return float(reserved), mode, reserve_value


def _next_month_start(d: date) -> date:
    if d.month == 12:
        return date(d.year + 1, 1, 1)
    return date(d.year, d.month + 1, 1)


async def _get_big_expense_totals(
    db: AsyncSession,
    family_id: int,
    year: Optional[int] = None,
    month: Optional[int] = None,
) -> dict:
    """Aggregate big-expense reserved/spent totals in USD."""
    rate_cache: dict[date, dict[int, float]] = {}
    total_reserved = 0.0
    total_spent = 0.0
    month_reserved = 0.0 if year is not None and month is not None else None
    month_spent = 0.0 if year is not None and month is not None else None

    income_rows = (
        await db.execute(
            select(
                Income.currency_id,
                Income.income_date,
                func.sum(Income.big_expense_reserved).label("reserved_sum"),
            ).where(
                Income.family_id == family_id,
                Income.big_expense_reserved > 0,
            ).group_by(
                Income.currency_id,
                Income.income_date,
            )
        )
    ).all()
    for currency_id, income_date, reserved_sum in income_rows:
        reserved = float(reserved_sum or 0)
        if reserved <= 0:
            continue
        usd_reserved = await convert_to_usd(
            db, reserved, int(currency_id), income_date, rate_cache
        )
        total_reserved += usd_reserved
        if month_reserved is not None and income_date.year == year and income_date.month == month:
            month_reserved += usd_reserved

    expense_rows = (
        await db.execute(
            select(
                Expense.currency_id,
                Expense.expense_date,
                func.sum(Expense.amount).label("amount_sum"),
            ).where(
                Expense.family_id == family_id,
                Expense.is_big_expense == True,
                Expense.split_only == False,
                Expense.allocation_source_id.is_(None),
                Expense.amount > 0,
            ).group_by(
                Expense.currency_id,
                Expense.expense_date,
            )
        )
    ).all()
    for currency_id, expense_date, amount_sum in expense_rows:
        amount = float(amount_sum or 0)
        if amount <= 0:
            continue
        usd_amount = await convert_to_usd(
            db, amount, int(currency_id), expense_date, rate_cache
        )
        total_spent += usd_amount
        if month_spent is not None and expense_date.year == year and expense_date.month == month:
            month_spent += usd_amount

    return {
        "reserved_total": total_reserved,
        "reserved_month": month_reserved,
        "expense_total": total_spent,
        "expense_month": month_spent,
        "balance_total": total_reserved - total_spent,
        "balance_month": (
            month_reserved - month_spent
            if month_reserved is not None and month_spent is not None
            else None
        ),
    }


@router.get("", response_model=PaginatedResponse[IncomeResponse])
async def get_incomes(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    user_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get incomes with filtering and pagination"""
    if not current_user.family_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You are not in a family")
    
    query = select(Income).where(Income.family_id == current_user.family_id)
    
    if start_date:
        query = query.where(Income.income_date >= start_date)
    if end_date:
        query = query.where(Income.income_date <= end_date)
    if user_id:
        query = query.where(Income.user_id == user_id)
    
    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar()
    
    # Get paginated results
    query = query.order_by(Income.income_date.desc(), Income.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    
    result = await db.execute(query.options(selectinload(Income.currency)))
    incomes = result.scalars().all()
    # attach currency_code to avoid lazy loading in Pydantic
    for income in incomes:
        if not getattr(income, "currency_code", None):
            income.currency_code = getattr(income.currency, "code", None)
    
    return PaginatedResponse(
        data=PaginatedData(
            items=[IncomeResponse.model_validate(i) for i in incomes],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=(total + page_size - 1) // page_size
        )
    )


@router.post("", response_model=SuccessResponse[IncomeResponse])
async def create_income(
    income_data: IncomeCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new income record"""
    if not current_user.family_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You are not in a family")
    
    reserved, mode, reserve_value = _calculate_reserved(
        income_data.amount,
        income_data.reserve_mode,
        income_data.reserve_value
    )
    
    income = Income(
        family_id=current_user.family_id,
        user_id=current_user.id,
        amount=income_data.amount,
        currency_id=income_data.currency_id,
        source=income_data.source,
        income_date=income_data.income_date,
        description=income_data.description,
        big_expense_reserved=reserved,
        reserve_mode=mode,
        reserve_value=reserve_value
    )
    db.add(income)
    await db.flush()
    await db.refresh(income, attribute_names=["currency"])
    income.currency_code = getattr(income.currency, "code", None)
    await invalidate_family_expense_cache(int(current_user.family_id))
    
    return SuccessResponse(
        data=IncomeResponse.model_validate(income),
        message="收入记录创建成功"
    )


@router.put("/{income_id}", response_model=SuccessResponse[IncomeResponse])
async def update_income(
    income_id: int,
    income_data: IncomeUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update an income record"""
    if not current_user.family_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You are not in a family")
    
    result = await db.execute(
        select(Income)
        .options(selectinload(Income.currency))
        .where(
            Income.id == income_id,
            Income.family_id == current_user.family_id
        )
    )
    income = result.scalar_one_or_none()
    
    if not income:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Income not found")
    
    # Prepare new values
    new_amount = income_data.amount if income_data.amount is not None else float(income.amount)
    new_mode = income_data.reserve_mode if income_data.reserve_mode is not None else income.reserve_mode
    new_value = income_data.reserve_value if income_data.reserve_value is not None else income.reserve_value
    
    reserved, mode, reserve_value = _calculate_reserved(new_amount, new_mode, new_value)
    
    # Update fields
    update_data = income_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(income, key, value)
    
    income.big_expense_reserved = reserved
    income.reserve_mode = mode
    income.reserve_value = reserve_value
    income.amount = new_amount
    
    await db.flush()
    await db.refresh(income, attribute_names=["currency"])
    income.currency_code = getattr(income.currency, "code", None)
    await invalidate_family_expense_cache(int(current_user.family_id))
    
    return SuccessResponse(
        data=IncomeResponse.model_validate(income),
        message="收入记录已更新"
    )


@router.delete("/{income_id}", response_model=SuccessResponse[dict])
async def delete_income(
    income_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete an income record"""
    if not current_user.family_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You are not in a family")
    
    result = await db.execute(
        select(Income).where(
            Income.id == income_id,
            Income.family_id == current_user.family_id
        )
    )
    income = result.scalar_one_or_none()
    
    if not income:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Income not found")
    
    await db.delete(income)
    await invalidate_family_expense_cache(int(current_user.family_id))
    
    return SuccessResponse(data={}, message="收入记录已删除")


@router.get("/stats/monthly", response_model=SuccessResponse[dict])
async def get_monthly_income_stats(
    year: int,
    month: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get monthly income statistics"""
    if not current_user.family_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You are not in a family")

    family_id = int(current_user.family_id)
    month_start = date(year, month, 1)
    next_month = _next_month_start(month_start)

    rate_cache: dict[date, dict[int, float]] = {}
    total_income = 0.0
    month_reserved = 0.0
    by_source: dict[str, float] = {}
    by_user: dict[int, float] = {}

    income_rows = (
        await db.execute(
            select(
                Income.source,
                Income.user_id,
                Income.currency_id,
                Income.income_date,
                func.sum(Income.amount).label("amount_sum"),
                func.sum(Income.big_expense_reserved).label("reserved_sum"),
            ).where(
                Income.family_id == family_id,
                Income.income_date >= month_start,
                Income.income_date < next_month,
            ).group_by(
                Income.source,
                Income.user_id,
                Income.currency_id,
                Income.income_date,
            )
        )
    ).all()

    for source_raw, uid, currency_id, income_date, amount_sum, reserved_sum in income_rows:
        source = source_raw or "其他"
        amount = float(amount_sum or 0)
        if amount > 0:
            usd_amount = await convert_to_usd(
                db, amount, int(currency_id), income_date, rate_cache
            )
            total_income += usd_amount
            by_source[source] = by_source.get(source, 0.0) + usd_amount
            by_user[int(uid)] = by_user.get(int(uid), 0.0) + usd_amount

        reserved = float(reserved_sum or 0)
        if reserved > 0:
            month_reserved += await convert_to_usd(
                db, reserved, int(currency_id), income_date, rate_cache
            )

    totals = await _get_big_expense_totals(db, family_id, year, month)
    total_reserved = totals["reserved_total"]
    total_big_expense_spent = totals["expense_total"]
    month_big_expense_spent = totals["expense_month"] or 0.0
    balance_total = totals["balance_total"]
    balance_month = totals["balance_month"] if totals["balance_month"] is not None else (month_reserved - month_big_expense_spent)
    
    return SuccessResponse(
        data={
            "year": year,
            "month": month,
            "total_income": total_income,
            "by_source": by_source,
            "by_user": by_user,
            "big_expense_reserved_month": month_reserved,
            "big_expense_reserved_total": total_reserved,
            "big_expense_expense_month": month_big_expense_spent,
            "big_expense_expense_total": total_big_expense_spent,
            "big_expense_balance_month": balance_month,
            "big_expense_balance_total": balance_total
        },
        message="获取成功"
    )


@router.get("/summary", response_model=SuccessResponse[dict])
async def get_income_summary(
    year: Optional[int] = None,
    month: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    汇总收入与大额开销预留情况
    """
    if not current_user.family_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You are not in a family")

    family_id = int(current_user.family_id)
    today = date.today()
    target_year = year or today.year
    target_month = month or today.month
    cache_key = (
        f"expense:stats:family:{family_id}:income-summary:"
        f"{target_year:04d}-{target_month:02d}"
    )
    cached = await cache.get(cache_key)
    if cached is not None:
        return SuccessResponse(data=cached, message="获取成功")

    month_start = date(target_year, target_month, 1)
    next_month = _next_month_start(month_start)

    rate_cache: dict[date, dict[int, float]] = {}
    month_income_total = 0.0
    month_reserved = 0.0

    month_rows = (
        await db.execute(
            select(
                Income.currency_id,
                Income.income_date,
                func.sum(Income.amount).label("amount_sum"),
                func.sum(Income.big_expense_reserved).label("reserved_sum"),
            ).where(
                Income.family_id == family_id,
                Income.income_date >= month_start,
                Income.income_date < next_month,
            ).group_by(
                Income.currency_id,
                Income.income_date,
            )
        )
    ).all()
    for currency_id, income_date, amount_sum, reserved_sum in month_rows:
        amount = float(amount_sum or 0)
        if amount > 0:
            month_income_total += await convert_to_usd(
                db, amount, int(currency_id), income_date, rate_cache
            )
        reserved = float(reserved_sum or 0)
        if reserved > 0:
            month_reserved += await convert_to_usd(
                db, reserved, int(currency_id), income_date, rate_cache
            )

    totals = await _get_big_expense_totals(db, family_id, target_year, target_month)
    total_reserved = totals["reserved_total"]
    total_big_expense_spent = totals["expense_total"]
    month_big_expense_spent = totals["expense_month"] or 0.0

    payload = {
        "year": target_year,
        "month": target_month,
        "income_month": month_income_total,
        "total_income_month": month_income_total,  # alias for UI compatibility
        "big_expense_reserved_month": month_reserved,
        "big_expense_reserved_total": total_reserved,
        "big_expense_expense_month": month_big_expense_spent,
        "big_expense_expense_total": total_big_expense_spent,
        "big_expense_balance_month": month_reserved - month_big_expense_spent,
        "big_expense_balance_total": total_reserved - total_big_expense_spent
    }
    await cache.set(cache_key, payload, ttl_seconds=120)

    return SuccessResponse(
        data=payload,
        message="获取成功"
    )
