"""
Trip and budget routes
"""
from datetime import date
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func, delete
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.models.trip import Trip, TripBudget, TripExpense
from app.models.currency import Currency
from app.models.expense import Expense, ExpenseSplit, ExpenseCategory
from app.schemas.trip import (
    TripCreate, TripUpdate, TripResponse,
    TripBudgetCreate, TripBudgetUpdate, TripBudgetResponse,
    TripExpenseCreate, TripExpenseUpdate, TripExpenseResponse, TripExpenseSplitBatch,
    TripStatsResponse, BudgetVsActual
)
from app.schemas.common import SuccessResponse
from app.utils.security import get_current_user
from app.socket.handlers import emit_trip_event
from app.services.split_allocation_service import sync_split_only_allocations
from app.services.split_allocation_service import delete_split_only_allocations
from app.services.level_service import delete_expense_diamond_spends
from app.utils.cache import invalidate_family_expense_cache

router = APIRouter(prefix="/trips", tags=["Trips"])


def _compute_trip_status(start: Optional[date], end: Optional[date]) -> str:
    """Determine trip status based on dates."""
    today = date.today()
    if start and end:
        if today < start:
            return "planned"
        if today > end:
            return "completed"
        return "active"
    if start and not end:
        return "planned" if today < start else "active"
    if not start and end:
        return "planned" if today < end else "completed"
    return "planned"


async def _resolve_currency_id(
    db: AsyncSession,
    currency_id: Optional[int],
    currency_code: Optional[str]
) -> Optional[int]:
    """
    Map currency code to ID if needed.
    Accepts either currency_id or currency_code (e.g., 'USD').
    """
    if currency_id:
        return currency_id
    if currency_code:
        result = await db.execute(
            select(Currency).where(Currency.code == currency_code.upper())
        )
        currency = result.scalar_one_or_none()
        if currency:
            return currency.id
    return None


def _trip_to_response(trip: Trip, total_spent: Optional[float] = None) -> TripResponse:
    """Normalize trip ORM object to TripResponse with currency code."""
    currency_code = trip.currency.code if getattr(trip, "currency", None) else None
    budget_value = float(trip.total_budget) if trip.total_budget is not None else None
    return TripResponse(
        id=trip.id,
        family_id=trip.family_id,
        name=trip.name,
        destination=trip.destination,
        start_date=trip.start_date,
        end_date=trip.end_date,
        total_budget=budget_value,
        currency_id=trip.currency_id,
        currency_code=currency_code,
        total_spent=float(total_spent) if total_spent is not None else None,
        status=trip.status,
        created_by=trip.created_by,
        created_at=trip.created_at,
    )


async def _recalculate_total_budget(db: AsyncSession, trip: Trip) -> float:
    """Recalculate and update trip total budget based on all budget rows."""
    result = await db.execute(
        select(func.coalesce(func.sum(TripBudget.budget_amount), 0)).where(
            TripBudget.trip_id == trip.id
        )
    )
    total = float(result.scalar_one() or 0)
    trip.total_budget = total
    return total


def _expense_to_response(
    expense: TripExpense,
    category: Optional[str],
    currency_code: Optional[str]
) -> TripExpenseResponse:
    """Normalize expense with category/currency code."""
    return TripExpenseResponse(
        id=expense.id,
        trip_id=expense.trip_id,
        budget_id=expense.budget_id,
        user_id=expense.user_id,
        amount=float(expense.amount),
        currency_id=expense.currency_id,
        currency_code=currency_code,
        split_source_expense_id=getattr(expense, "split_source_expense_id", None),
        category=category,
        description=expense.description,
        expense_date=expense.expense_date,
        created_at=expense.created_at,
    )


def _split_equal_amounts(total_amount: float, participants: List[int]) -> List[float]:
    """Split amount equally (2 decimals) and ensure sum matches via remainder distribution."""
    n = len(participants)
    if n <= 0:
        return []
    cents = int(round(float(total_amount) * 100))
    base = cents // n
    remainder = cents % n
    shares = []
    for i in range(n):
        share_cents = base + (1 if i < remainder else 0)
        shares.append(round(share_cents / 100.0, 2))
    return shares


def _build_trip_split_description(trip: Trip, category: Optional[str], description: Optional[str]) -> str:
    base = (description or "").strip()
    cat = (category or "其他").strip()
    if base:
        return f"旅行均摊｜{trip.name}｜{cat}｜{base}"
    return f"旅行均摊｜{trip.name}｜{cat}"


async def _sync_trip_split_source_expense(
    db: AsyncSession,
    trip: Trip,
    trip_expense: TripExpense,
    category_name: Optional[str],
    family_id: int,
) -> None:
    """
    Keep linked split-only source expense in sync when a trip expense is edited.
    """
    source_id = getattr(trip_expense, "split_source_expense_id", None)
    if not source_id:
        return

    source_expense = await db.scalar(
        select(Expense)
        .options(selectinload(Expense.splits))
        .where(
            Expense.id == int(source_id),
            Expense.family_id == family_id,
        )
    )
    if not source_expense:
        return

    source_expense.user_id = int(trip_expense.user_id)
    source_expense.amount = float(trip_expense.amount)
    currency_id = trip_expense.currency_id or source_expense.currency_id or trip.currency_id
    if currency_id:
        source_expense.currency_id = int(currency_id)
    source_expense.expense_date = trip_expense.expense_date or trip.start_date or date.today()
    source_expense.description = _build_trip_split_description(trip, category_name, trip_expense.description)

    # Keep original split participants; recalculate equal shares for updated amount.
    split_rows = list(source_expense.splits or [])
    if split_rows:
        participant_ids = [int(s.user_id) for s in split_rows]
        shares = _split_equal_amounts(float(trip_expense.amount or 0), participant_ids)
        for idx, split in enumerate(split_rows):
            split.share_amount = shares[idx]
            split.share_percentage = None

    await db.flush()
    await sync_split_only_allocations(db, int(source_expense.id))


@router.get("", response_model=SuccessResponse[List[TripResponse]])
async def get_trips(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all trips for the family"""
    if not current_user.family_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You are not in a family")
    
    result = await db.execute(
        select(Trip)
        .options(selectinload(Trip.currency))
        .where(Trip.family_id == current_user.family_id)
        .order_by(Trip.start_date.desc())
    )
    trips = result.scalars().all()

    if not trips:
        return SuccessResponse(data=[], message="获取成功")

    trip_ids = [t.id for t in trips]

    # Pre-compute total spent per trip
    spent_rows = await db.execute(
        select(
            TripExpense.trip_id,
            func.coalesce(func.sum(TripExpense.amount), 0).label("spent")
        )
        .where(TripExpense.trip_id.in_(trip_ids))
        .group_by(TripExpense.trip_id)
    )
    spent_map = {row[0]: float(row[1] or 0) for row in spent_rows.all()}

    # Pre-compute total budget per trip to keep cards in sync
    budget_rows = await db.execute(
        select(
            TripBudget.trip_id,
            func.coalesce(func.sum(TripBudget.budget_amount), 0).label("budget")
        )
        .where(TripBudget.trip_id.in_(trip_ids))
        .group_by(TripBudget.trip_id)
    )
    budget_map = {row[0]: float(row[1] or 0) for row in budget_rows.all()}

    # Ensure status and totals match current dates/data
    status_changed = False
    budget_changed = False
    for trip in trips:
        computed_status = _compute_trip_status(trip.start_date, trip.end_date)
        if trip.status != computed_status:
            trip.status = computed_status
            status_changed = True

        if trip.id in budget_map:
            computed_budget = budget_map[trip.id]
            current_budget = float(trip.total_budget) if trip.total_budget is not None else 0.0
            if computed_budget > 0 and abs(current_budget - computed_budget) > 0.009:
                trip.total_budget = computed_budget
                budget_changed = True

    if status_changed or budget_changed:
        await db.flush()
        await db.commit()
    
    return SuccessResponse(
        data=[_trip_to_response(t, spent_map.get(t.id, 0)) for t in trips],
        message="获取成功"
    )


@router.post("", response_model=SuccessResponse[TripResponse])
async def create_trip(
    trip_data: TripCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new trip"""
    if not current_user.family_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You are not in a family")

    currency_id = await _resolve_currency_id(db, trip_data.currency_id, trip_data.currency_code)
    
    trip = Trip(
        family_id=current_user.family_id,
        name=trip_data.name,
        destination=trip_data.destination,
        start_date=trip_data.start_date,
        end_date=trip_data.end_date,
        total_budget=trip_data.total_budget,
        currency_id=currency_id,
        created_by=current_user.id,
        status=_compute_trip_status(trip_data.start_date, trip_data.end_date)
    )
    db.add(trip)
    await db.flush()
    await db.refresh(trip, attribute_names=["currency"])
    
    trip_response = _trip_to_response(trip, 0)
    
    # Broadcast socket event
    await emit_trip_event("created", trip_response.model_dump(mode='json'), current_user.family_id)
    
    return SuccessResponse(
        data=trip_response,
        message="旅行计划创建成功"
    )


@router.get("/{trip_id}", response_model=SuccessResponse[TripResponse])
async def get_trip(
    trip_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific trip"""
    if not current_user.family_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You are not in a family")
    
    result = await db.execute(
        select(Trip)
        .options(
            selectinload(Trip.currency),
            selectinload(Trip.budgets),
            selectinload(Trip.expenses)
        )
        .where(
            Trip.id == trip_id,
            Trip.family_id == current_user.family_id
        )
    )
    trip = result.scalar_one_or_none()
    
    if not trip:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found")
    
    total_spent = sum(float(e.amount) for e in trip.expenses)
    
    return SuccessResponse(data=_trip_to_response(trip, total_spent), message="获取成功")


@router.put("/{trip_id}", response_model=SuccessResponse[TripResponse])
async def update_trip(
    trip_id: int,
    trip_data: TripUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a trip"""
    if not current_user.family_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You are not in a family")
    
    result = await db.execute(
        select(Trip).where(
            Trip.id == trip_id,
            Trip.family_id == current_user.family_id
        )
    )
    trip = result.scalar_one_or_none()
    
    if not trip:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found")
    
    # Update fields
    update_data = trip_data.model_dump(exclude_unset=True)
    currency_code = update_data.pop("currency_code", None)
    if currency_code or update_data.get("currency_id"):
        update_data["currency_id"] = await _resolve_currency_id(
            db,
            update_data.get("currency_id"),
            currency_code
        )
    for key, value in update_data.items():
        setattr(trip, key, value)

    # Auto-update status based on dates
    trip.status = _compute_trip_status(trip.start_date, trip.end_date)
    
    await db.flush()
    await db.refresh(trip, attribute_names=["currency"])
    
    spent_res = await db.execute(
        select(func.coalesce(func.sum(TripExpense.amount), 0)).where(
            TripExpense.trip_id == trip_id
        )
    )
    total_spent = float(spent_res.scalar_one() or 0)
    trip_response = _trip_to_response(trip, total_spent)
    
    # Broadcast socket event
    await emit_trip_event("updated", trip_response.model_dump(mode='json'), current_user.family_id)
    
    return SuccessResponse(
        data=trip_response,
        message="旅行计划已更新"
    )


@router.delete("/{trip_id}", response_model=SuccessResponse[dict])
async def delete_trip(
    trip_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a trip"""
    if not current_user.family_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You are not in a family")
    
    result = await db.execute(
        select(Trip).where(
            Trip.id == trip_id,
            Trip.family_id == current_user.family_id
        )
    )
    trip = result.scalar_one_or_none()
    
    if not trip:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found")
    
    deleted_trip_id = trip.id
    await db.delete(trip)
    
    # Broadcast socket event
    await emit_trip_event("deleted", {"id": deleted_trip_id}, current_user.family_id)
    
    return SuccessResponse(data={}, message="旅行计划已删除")


# ============== Budgets ==============

@router.post("/{trip_id}/budgets", response_model=SuccessResponse[TripBudgetResponse])
async def create_trip_budget(
    trip_id: int,
    budget_data: TripBudgetCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Add a budget category to a trip"""
    if not current_user.family_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You are not in a family")
    
    # Verify trip exists and belongs to family
    result = await db.execute(
        select(Trip)
        .options(selectinload(Trip.currency))
        .where(
            Trip.id == trip_id,
            Trip.family_id == current_user.family_id
        )
    )
    trip = result.scalar_one_or_none()
    
    if not trip:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found")
    
    budget = TripBudget(
        trip_id=trip_id,
        category=budget_data.category,
        budget_amount=budget_data.budget_amount
    )
    db.add(budget)
    await db.flush()
    await db.refresh(budget)
    await _recalculate_total_budget(db, trip)
    
    response = TripBudgetResponse.model_validate(budget)
    response.spent_amount = 0
    
    # Broadcast socket event
    await emit_trip_event("budget_added", response.model_dump(mode='json'), current_user.family_id)
    
    return SuccessResponse(
        data=response,
        message="预算分类添加成功"
    )


@router.get("/{trip_id}/budgets", response_model=SuccessResponse[List[TripBudgetResponse]])
async def get_trip_budgets(
    trip_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all budgets for a trip with spent amounts."""
    if not current_user.family_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You are not in a family")

    # Verify trip belongs to family
    result = await db.execute(
        select(Trip).where(
            Trip.id == trip_id,
            Trip.family_id == current_user.family_id
        )
    )
    trip = result.scalar_one_or_none()
    if not trip:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found")

    query = await db.execute(
        select(
            TripBudget,
            func.coalesce(func.sum(TripExpense.amount), 0).label("spent")
        )
        .outerjoin(TripExpense, TripExpense.budget_id == TripBudget.id)
        .where(TripBudget.trip_id == trip_id)
        .group_by(TripBudget.id)
        .order_by(TripBudget.id)
    )

    budgets: List[TripBudgetResponse] = []
    for budget, spent in query.all():
        budgets.append(
            TripBudgetResponse(
                id=budget.id,
                trip_id=budget.trip_id,
                category=budget.category,
                budget_amount=float(budget.budget_amount),
                spent_amount=float(spent or 0),
            )
        )

    return SuccessResponse(data=budgets, message="获取成功")


@router.put("/{trip_id}/budgets/{budget_id}", response_model=SuccessResponse[TripBudgetResponse])
async def update_trip_budget(
    trip_id: int,
    budget_id: int,
    budget_data: TripBudgetUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a budget category"""
    if not current_user.family_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You are not in a family")

    # Verify trip and budget belong to family
    trip_result = await db.execute(
        select(Trip).where(
            Trip.id == trip_id,
            Trip.family_id == current_user.family_id
        )
    )
    trip = trip_result.scalar_one_or_none()
    if not trip:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found")

    budget_result = await db.execute(
        select(TripBudget).where(
            TripBudget.id == budget_id,
            TripBudget.trip_id == trip_id
        )
    )
    budget = budget_result.scalar_one_or_none()
    if not budget:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Budget not found")

    update_fields = budget_data.model_dump(exclude_unset=True)
    for key, value in update_fields.items():
        setattr(budget, key, value)

    await db.flush()
    await db.refresh(budget)
    await _recalculate_total_budget(db, trip)

    spent_res = await db.execute(
        select(func.coalesce(func.sum(TripExpense.amount), 0)).where(
            TripExpense.budget_id == budget.id
        )
    )
    spent_amount = float(spent_res.scalar_one() or 0)

    response = TripBudgetResponse(
        id=budget.id,
        trip_id=budget.trip_id,
        category=budget.category,
        budget_amount=float(budget.budget_amount),
        spent_amount=spent_amount,
    )

    await emit_trip_event("budget_updated", response.model_dump(mode='json'), current_user.family_id)

    return SuccessResponse(data=response, message="预算分类已更新")


# ============== Expenses ==============

@router.post("/{trip_id}/expenses", response_model=SuccessResponse[TripExpenseResponse])
async def create_trip_expense(
    trip_id: int,
    expense_data: TripExpenseCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Add an expense to a trip"""
    if not current_user.family_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You are not in a family")
    
    # Verify trip exists and belongs to family
    result = await db.execute(
        select(Trip).where(
            Trip.id == trip_id,
            Trip.family_id == current_user.family_id
        )
    )
    trip = result.scalar_one_or_none()
    
    if not trip:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found")
    
    # Resolve currency (support code/id, fallback to trip currency)
    currency_id = await _resolve_currency_id(
        db,
        expense_data.currency_id or trip.currency_id,
        expense_data.currency_code
    ) or trip.currency_id

    # Fetch budget to attach category if provided
    category_name: Optional[str] = None
    if expense_data.budget_id:
        budget_res = await db.execute(
            select(TripBudget).where(
                TripBudget.id == expense_data.budget_id,
                TripBudget.trip_id == trip_id
            )
        )
        budget = budget_res.scalar_one_or_none()
        if not budget:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Budget not found")
        category_name = budget.category
    
    expense = TripExpense(
        trip_id=trip_id,
        budget_id=expense_data.budget_id,
        user_id=current_user.id,
        amount=expense_data.amount,
        currency_id=currency_id,
        description=expense_data.description,
        expense_date=expense_data.expense_date
    )
    db.add(expense)
    await db.flush()
    await db.refresh(expense)

    currency_code = None
    if currency_id:
        cur_res = await db.execute(select(Currency).where(Currency.id == currency_id))
        currency = cur_res.scalar_one_or_none()
        currency_code = currency.code if currency else None
    category_name = category_name or "其他"
    
    expense_response = _expense_to_response(expense, category_name, currency_code)
    
    # Broadcast socket event
    await emit_trip_event("expense_added", expense_response.model_dump(mode='json'), current_user.family_id)
    
    return SuccessResponse(
        data=expense_response,
        message="旅行支出添加成功"
    )


@router.get("/{trip_id}/expenses", response_model=SuccessResponse[List[TripExpenseResponse]])
async def get_trip_expenses(
    trip_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all expenses for a trip (with category & currency code)."""
    if not current_user.family_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You are not in a family")

    # Ensure trip belongs to family
    trip_res = await db.execute(
        select(Trip).where(
            Trip.id == trip_id,
            Trip.family_id == current_user.family_id
        )
    )
    trip = trip_res.scalar_one_or_none()
    if not trip:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found")

    result = await db.execute(
        select(
            TripExpense,
            TripBudget.category,
            Currency.code
        )
        .join(Trip, Trip.id == TripExpense.trip_id)
        .outerjoin(TripBudget, TripExpense.budget_id == TripBudget.id)
        .outerjoin(Currency, TripExpense.currency_id == Currency.id)
        .where(
            TripExpense.trip_id == trip_id,
            Trip.family_id == current_user.family_id
        )
        .order_by(TripExpense.expense_date.desc().nullslast(), TripExpense.created_at.desc())
    )

    expenses: List[TripExpenseResponse] = []
    for expense, category, currency_code in result.all():
        expenses.append(_expense_to_response(expense, category, currency_code))

    return SuccessResponse(data=expenses, message="获取成功")


@router.put("/{trip_id}/expenses/{expense_id}", response_model=SuccessResponse[TripExpenseResponse])
async def update_trip_expense(
    trip_id: int,
    expense_id: int,
    expense_data: TripExpenseUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a specific trip expense"""
    if not current_user.family_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You are not in a family")

    trip = await db.scalar(
        select(Trip).where(
            Trip.id == trip_id,
            Trip.family_id == current_user.family_id,
        )
    )
    if not trip:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found")

    expense = await db.scalar(
        select(TripExpense).where(
            TripExpense.id == expense_id,
            TripExpense.trip_id == trip_id,
        )
    )
    if not expense:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Expense not found")

    payload = expense_data.model_dump(exclude_unset=True, by_alias=False)
    currency_code = payload.pop("currency_code", None)
    if payload.get("amount") is None:
        payload.pop("amount", None)
    if payload.get("user_id") is None:
        payload.pop("user_id", None)

    # Validate payer if changed
    if "user_id" in payload and payload.get("user_id") is not None:
        payer = await db.scalar(
            select(User).where(
                User.id == int(payload["user_id"]),
                User.family_id == current_user.family_id,
            )
        )
        if not payer:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="付款人不存在或不在家庭中")

    # Validate/resolve budget
    budget_for_response: Optional[TripBudget] = None
    if "budget_id" in payload:
        incoming_budget_id = payload.get("budget_id")
        if incoming_budget_id is None or int(incoming_budget_id) <= 0:
            payload["budget_id"] = None
        else:
            budget_for_response = await db.scalar(
                select(TripBudget).where(
                    TripBudget.id == int(incoming_budget_id),
                    TripBudget.trip_id == trip_id,
                )
            )
            if not budget_for_response:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Budget not found")
            payload["budget_id"] = int(incoming_budget_id)

    # Validate/resolve currency
    resolved_currency_id: Optional[int] = None
    if "currency_id" in payload and payload.get("currency_id") is not None:
        cid = int(payload["currency_id"])
        existing_currency = await db.scalar(select(Currency.id).where(Currency.id == cid))
        if not existing_currency:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Currency not found")
        resolved_currency_id = cid
    if currency_code:
        resolved_currency_id = await _resolve_currency_id(db, None, currency_code)
        if not resolved_currency_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Currency not found")
    if resolved_currency_id is not None:
        payload["currency_id"] = resolved_currency_id
    elif "currency_id" in payload and payload.get("currency_id") is None:
        payload.pop("currency_id", None)

    for key, value in payload.items():
        setattr(expense, key, value)

    await db.flush()
    await db.refresh(expense)

    # If budget unchanged in this request, resolve the existing category for response/sync logic.
    if budget_for_response is None and expense.budget_id:
        budget_for_response = await db.scalar(
            select(TripBudget).where(
                TripBudget.id == expense.budget_id,
                TripBudget.trip_id == trip_id,
            )
        )

    currency = None
    if expense.currency_id:
        currency = await db.scalar(select(Currency).where(Currency.id == expense.currency_id))
    currency_code_for_response = currency.code if currency else None
    category_name = budget_for_response.category if budget_for_response else "其他"

    await _sync_trip_split_source_expense(
        db=db,
        trip=trip,
        trip_expense=expense,
        category_name=category_name,
        family_id=int(current_user.family_id),
    )

    response = _expense_to_response(expense, category_name, currency_code_for_response)
    await emit_trip_event("expense_updated", response.model_dump(mode="json"), current_user.family_id)

    return SuccessResponse(data=response, message="旅行支出已更新")


@router.post("/{trip_id}/expenses/split", response_model=SuccessResponse[List[TripExpenseResponse]])
async def split_trip_expenses(
    trip_id: int,
    payload: TripExpenseSplitBatch,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Batch create/update split-only expenses for selected trip expenses (AA settlement)."""
    if not current_user.family_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You are not in a family")

    expense_ids = sorted({int(i) for i in (payload.expense_ids or []) if int(i) > 0})
    split_user_ids = [int(i) for i in (payload.split_user_ids or []) if int(i) > 0]
    # Preserve caller order for remainder distribution, but ensure uniqueness
    seen = set()
    split_user_ids = [i for i in split_user_ids if not (i in seen or seen.add(i))]

    if not expense_ids:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="请选择需要均摊的支出")
    if not split_user_ids:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="请选择均摊成员")

    trip = await db.scalar(
        select(Trip).where(
            Trip.id == trip_id,
            Trip.family_id == current_user.family_id,
        )
    )
    if not trip:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found")

    # Validate split members in family
    split_users_result = await db.execute(
        select(User.id).where(
            User.id.in_(split_user_ids),
            User.family_id == current_user.family_id,
        )
    )
    valid_split_ids = {int(r[0]) for r in split_users_result.all()}
    invalid_split_ids = [uid for uid in split_user_ids if uid not in valid_split_ids]
    if invalid_split_ids:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"分摊成员不存在或不在家庭中: {invalid_split_ids}",
        )

    # Choose a category for generated settlement expenses (prefer '旅游', fallback to '其他')
    category_rows = await db.execute(
        select(ExpenseCategory).where(
            ExpenseCategory.family_id == current_user.family_id,
            ExpenseCategory.name.in_(["旅游", "其他"]),
        )
    )
    categories = list(category_rows.scalars().all())
    category = next((c for c in categories if c.name == "旅游"), None) or next(
        (c for c in categories if c.name == "其他"), None
    )
    if not category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="请先创建支出分类（如：旅游/其他）")

    fallback_currency_id = trip.currency_id
    if not fallback_currency_id:
        fallback_currency_id = await db.scalar(select(Currency.id).where(Currency.code == "CNY"))
    if not fallback_currency_id:
        fallback_currency_id = await db.scalar(select(Currency.id).order_by(Currency.id.asc()).limit(1))
    if not fallback_currency_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="系统未配置货币")

    # Load trip expenses (+ budget category + currency code) for response
    result = await db.execute(
        select(
            TripExpense,
            TripBudget.category,
            Currency.code,
        )
        .outerjoin(TripBudget, TripExpense.budget_id == TripBudget.id)
        .outerjoin(Currency, TripExpense.currency_id == Currency.id)
        .where(
            TripExpense.trip_id == trip_id,
            TripExpense.id.in_(expense_ids),
        )
    )
    rows = result.all()
    found_ids = {int(exp.id) for exp, _, _ in rows}
    missing = [eid for eid in expense_ids if eid not in found_ids]
    if missing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"支出不存在: {missing}")

    updated: List[TripExpenseResponse] = []
    for trip_expense, cat_name, currency_code in rows:
        amount = float(trip_expense.amount or 0)
        if amount <= 0:
            continue

        expense_date = trip_expense.expense_date or trip.start_date or date.today()
        currency_id = trip_expense.currency_id or fallback_currency_id
        description = _build_trip_split_description(trip, cat_name, trip_expense.description)

        source_expense: Optional[Expense] = None
        if getattr(trip_expense, "split_source_expense_id", None):
            source_expense = await db.scalar(
                select(Expense)
                .options(selectinload(Expense.splits))
                .where(
                    Expense.id == trip_expense.split_source_expense_id,
                    Expense.family_id == current_user.family_id,
                )
            )
            if source_expense and not source_expense.split_only:
                source_expense = None

        if not source_expense:
            source_expense = Expense(
                family_id=current_user.family_id,
                category_id=category.id,
                user_id=int(trip_expense.user_id),
                amount=amount,
                currency_id=int(currency_id),
                description=description,
                expense_date=expense_date,
                is_big_expense=False,
                split_only=True,
            )
            db.add(source_expense)
            await db.flush()
            trip_expense.split_source_expense_id = int(source_expense.id)
            await db.flush()
        else:
            source_expense.category_id = int(category.id)
            source_expense.user_id = int(trip_expense.user_id)
            source_expense.amount = amount
            source_expense.currency_id = int(currency_id)
            source_expense.description = description
            source_expense.expense_date = expense_date
            source_expense.split_only = True
            await db.flush()

        # Reset splits then re-create equal shares
        await db.execute(delete(ExpenseSplit).where(ExpenseSplit.expense_id == source_expense.id))
        shares = _split_equal_amounts(amount, split_user_ids)
        for user_id, share_amount in zip(split_user_ids, shares):
            db.add(
                ExpenseSplit(
                    expense_id=int(source_expense.id),
                    user_id=int(user_id),
                    share_amount=float(share_amount),
                    share_percentage=None,
                )
            )
        await db.flush()

        # Generate derived allocation expenses for split-only records
        await sync_split_only_allocations(db, int(source_expense.id))

        updated.append(_expense_to_response(trip_expense, cat_name, currency_code))

    await invalidate_family_expense_cache(current_user.family_id)
    await emit_trip_event(
        "expense_split_updated",
        {"trip_id": trip_id, "expense_ids": expense_ids},
        current_user.family_id,
    )

    return SuccessResponse(data=updated, message="均摊已生成")


@router.delete("/{trip_id}/expenses/{expense_id}", response_model=SuccessResponse[dict])
async def delete_trip_expense(
    trip_id: int,
    expense_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a specific trip expense"""
    if not current_user.family_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You are not in a family")

    expense_res = await db.execute(
        select(TripExpense)
        .join(Trip, Trip.id == TripExpense.trip_id)
        .where(
            TripExpense.id == expense_id,
            TripExpense.trip_id == trip_id,
            Trip.family_id == current_user.family_id
        )
    )
    expense = expense_res.scalar_one_or_none()
    if not expense:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Expense not found")

    # If this trip expense has generated a split-only settlement expense in the main ledger,
    # delete that source expense (and its derived allocation expenses) as well.
    split_source_id = getattr(expense, "split_source_expense_id", None)
    if split_source_id:
        split_source = await db.scalar(
            select(Expense).where(
                Expense.id == int(split_source_id),
                Expense.family_id == current_user.family_id,
            )
        )
        if split_source:
            await delete_split_only_allocations(db, int(split_source.id))
            await db.execute(delete(ExpenseSplit).where(ExpenseSplit.expense_id == int(split_source.id)))
            await delete_expense_diamond_spends(db, int(split_source.id))
            await db.delete(split_source)
            await invalidate_family_expense_cache(current_user.family_id)

    await db.delete(expense)
    await emit_trip_event("expense_deleted", {"id": expense_id, "trip_id": trip_id}, current_user.family_id)

    return SuccessResponse(data={}, message="旅行支出已删除")


# ============== Statistics ==============

@router.get("/{trip_id}/stats", response_model=SuccessResponse[TripStatsResponse])
async def get_trip_stats(
    trip_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get budget vs actual statistics for a trip"""
    if not current_user.family_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You are not in a family")
    
    # Get trip with budgets and expenses
    result = await db.execute(
        select(Trip)
        .options(selectinload(Trip.budgets), selectinload(Trip.expenses))
        .where(
            Trip.id == trip_id,
            Trip.family_id == current_user.family_id
        )
    )
    trip = result.scalar_one_or_none()
    
    if not trip:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found")
    
    # Calculate totals
    total_budget = float(trip.total_budget or 0)
    total_spent = sum(float(e.amount) for e in trip.expenses)
    
    # Calculate by category
    category_stats = []
    budget_spent = {b.id: 0 for b in trip.budgets}
    
    for expense in trip.expenses:
        if expense.budget_id:
            budget_spent[expense.budget_id] += float(expense.amount)
    
    for budget in trip.budgets:
        spent = budget_spent.get(budget.id, 0)
        budget_amount = float(budget.budget_amount)
        remaining = budget_amount - spent
        percentage = (spent / budget_amount * 100) if budget_amount > 0 else 0
        
        category_stats.append(BudgetVsActual(
            category=budget.category,
            budget=budget_amount,
            actual=spent,
            remaining=remaining,
            percentage_used=round(percentage, 2)
        ))
    
    return SuccessResponse(
        data=TripStatsResponse(
            trip_id=trip_id,
            total_budget=total_budget,
            total_spent=total_spent,
            total_remaining=total_budget - total_spent,
            by_category=category_stats
        ),
        message="获取成功"
    )
