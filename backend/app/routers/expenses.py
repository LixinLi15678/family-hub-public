"""
Expense routes
"""
from datetime import date, datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select, func, and_, exists, or_
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.models.currency import Currency
from app.models.expense import Expense, ExpenseCategory, ExpenseSplit, Income
from app.services.level_service import rebuild_expense_diamond_spends, delete_expense_diamond_spends
from app.services.split_allocation_service import sync_split_only_allocations, delete_split_only_allocations
from app.services.exchange_rate_service import convert_to_usd
from app.utils.seed_data import seed_expense_categories
from app.schemas.expense import (
    ExpenseCategoryCreate, ExpenseCategoryResponse,
    ExpenseCreate, ExpenseUpdate, ExpenseResponse,
    ExpenseSplitCreate, ExpenseSplitResponse,
    MonthlyStats, CategoryStats, SplitSettlement,
    BigExpenseBudgetSummary, BigExpenseHistoryItem
)
from app.schemas.common import SuccessResponse, PaginatedResponse, PaginatedData
from app.utils.security import get_current_user
from app.utils.cache import cache, invalidate_family_expense_cache

router = APIRouter(prefix="/expenses", tags=["Expenses"])


# ============== Helpers ==============

def _next_month_start(d: date) -> date:
    if d.month == 12:
        return date(d.year + 1, 1, 1)
    return date(d.year, d.month + 1, 1)


def _add_months(month_start: date, delta: int) -> date:
    """Add months to a date anchored at day=1."""
    total = (month_start.year * 12 + (month_start.month - 1)) + delta
    year = total // 12
    month = total % 12 + 1
    return date(year, month, 1)

async def _get_big_expense_totals(
    db: AsyncSession,
    family_id: int,
    year: Optional[int] = None,
    month: Optional[int] = None
) -> dict:
    """Aggregate reserved/spent totals for big expenses."""
    rate_cache: dict[date, dict[int, float]] = {}
    total_reserved = 0.0
    total_spent = 0.0
    month_reserved = 0.0 if year is not None and month is not None else None
    month_spent = 0.0 if year is not None and month is not None else None

    # Aggregate by (currency_id, date) to avoid scanning & converting row-by-row.
    income_result = await db.execute(
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
    for currency_id, income_date, reserved_sum in income_result.all():
        reserved = float(reserved_sum or 0)
        if reserved <= 0:
            continue
        usd_reserved = await convert_to_usd(
            db, reserved, int(currency_id), income_date, rate_cache
        )
        total_reserved += usd_reserved
        if month_reserved is not None and income_date.year == year and income_date.month == month:
            month_reserved += usd_reserved

    expense_result = await db.execute(
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
    for currency_id, expense_date, amount_sum in expense_result.all():
        amount = float(amount_sum or 0)
        if amount <= 0:
            continue
        usd_amount = await convert_to_usd(
            db, amount, int(currency_id), expense_date, rate_cache
        )
        total_spent += usd_amount
        if month_spent is not None and expense_date.year == year and expense_date.month == month:
            month_spent += usd_amount

    balance_total = total_reserved - total_spent
    balance_month = (
        month_reserved - month_spent) if month_reserved is not None and month_spent is not None else None

    return {
        "reserved_total": total_reserved,
        "reserved_month": month_reserved,
        "expense_total": total_spent,
        "expense_month": month_spent,
        "balance_total": balance_total,
        "balance_month": balance_month
    }


# ============== Categories ==============

@router.get("/categories", response_model=SuccessResponse[List[ExpenseCategoryResponse]])
async def get_categories(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all expense categories"""
    if not current_user.family_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="You are not in a family")

    # Ensure new default categories are present (idempotent)
    await seed_expense_categories(db, current_user.family_id)

    result = await db.execute(
        select(ExpenseCategory)
        .options(
            selectinload(ExpenseCategory.children).selectinload(
                ExpenseCategory.children)
        )
        .where(ExpenseCategory.family_id == current_user.family_id)
        .order_by(ExpenseCategory.type, ExpenseCategory.sort_order)
    )
    categories = result.scalars().all()

    # Build hierarchy
    category_dict = {
        c.id: ExpenseCategoryResponse.model_validate(c) for c in categories}
    root_categories = []

    for cat in categories:
        cat_response = category_dict[cat.id]
        if cat.parent_id and cat.parent_id in category_dict:
            parent = category_dict[cat.parent_id]
            if parent.children is None:
                parent.children = []
            parent.children.append(cat_response)
        else:
            root_categories.append(cat_response)

    return SuccessResponse(data=root_categories, message="获取成功")


@router.post("/categories", response_model=SuccessResponse[ExpenseCategoryResponse])
async def create_category(
    category_data: ExpenseCategoryCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new expense category"""
    if not current_user.family_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="You are not in a family")

    category = ExpenseCategory(
        family_id=current_user.family_id,
        name=category_data.name,
        type=category_data.type,
        parent_id=category_data.parent_id,
        icon=category_data.icon,
        sort_order=category_data.sort_order,
        is_big_expense=category_data.is_big_expense
    )
    db.add(category)
    await db.flush()
    await db.refresh(category)

    # Ensure relationships are loaded (no lazy load during serialization)
    # Use explicit select with selectinload to avoid MissingGreenlet
    result = await db.execute(
        select(ExpenseCategory)
        .options(selectinload(ExpenseCategory.children))
        .where(ExpenseCategory.id == category.id)
    )
    category = result.scalar_one()

    return SuccessResponse(
        data=ExpenseCategoryResponse.model_validate(category),
        message="分类创建成功"
    )


# ============== Expenses ==============

@router.get("", response_model=PaginatedResponse[ExpenseResponse])
async def get_expenses(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    category_id: Optional[int] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    user_id: Optional[int] = None,
    split_user_id: Optional[int] = None,
    user_filter_mode: str = Query("or", pattern="^(or|and)$"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get expenses with filtering and pagination"""
    if not current_user.family_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="You are not in a family")

    # Build query for ledger history:
    # - include source split-only records (for highlighted history)
    # - exclude derived allocation records (internal rows for split accounting)
    query = select(Expense).where(
        Expense.family_id == current_user.family_id,
        Expense.allocation_source_id.is_(None),
    )

    if category_id:
        query = query.where(Expense.category_id == category_id)
    if start_date:
        query = query.where(Expense.expense_date >= start_date)
    if end_date:
        query = query.where(Expense.expense_date <= end_date)

    split_exists = None
    if split_user_id:
        split_exists = exists(
            select(1).where(
                ExpenseSplit.expense_id == Expense.id,
                ExpenseSplit.user_id == split_user_id,
            )
        )

    if user_id and split_exists is not None:
        if user_filter_mode == "and":
            query = query.where(Expense.user_id == user_id, split_exists)
        else:
            query = query.where(or_(Expense.user_id == user_id, split_exists))
    elif user_id:
        query = query.where(Expense.user_id == user_id)
    elif split_exists is not None:
        query = query.where(split_exists)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar()

    # Get paginated results
    query = query.options(selectinload(Expense.splits))
    query = query.order_by(Expense.expense_date.desc(),
                           Expense.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    expenses = result.scalars().all()

    return PaginatedResponse(
        data=PaginatedData(
            items=[ExpenseResponse.model_validate(e) for e in expenses],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=(total + page_size - 1) // page_size
        )
    )


@router.post("", response_model=SuccessResponse[ExpenseResponse])
async def create_expense(
    expense_data: ExpenseCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new expense"""
    if not current_user.family_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="You are not in a family")

    if expense_data.split_only and not expense_data.splits:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="仅分摊支出需要设置分摊成员"
        )

    # 查询分类以决定是否为大额开销
    category_result = await db.execute(
        select(ExpenseCategory).where(
            ExpenseCategory.id == expense_data.category_id,
            ExpenseCategory.family_id == current_user.family_id
        )
    )
    category = category_result.scalar_one_or_none()
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="分类不存在")

    is_big_expense = expense_data.is_big_expense if expense_data.is_big_expense is not None else bool(
        category.is_big_expense)

    # Validate currency exists to avoid FK IntegrityError -> 500
    currency_exists = await db.scalar(
        select(exists().where(Currency.id == expense_data.currency_id))
    )
    if not currency_exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="货币不存在"
        )

    # Only big-expense writes need balance snapshots; skip heavy aggregation otherwise.
    should_compute_big_pool = bool(is_big_expense)
    balance_before: Optional[float] = None
    if should_compute_big_pool:
        totals_before = await _get_big_expense_totals(db, current_user.family_id)
        balance_before = totals_before["balance_total"]

    # Determine payer (must be in same family)
    payer_id = current_user.id
    if expense_data.user_id is not None:
        payer_result = await db.execute(
            select(User).where(
                User.id == expense_data.user_id,
                User.family_id == current_user.family_id
            )
        )
        payer = payer_result.scalar_one_or_none()
        if not payer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="付款人不存在或不在家庭中")
        payer_id = payer.id

    expense = Expense(
        family_id=current_user.family_id,
        category_id=expense_data.category_id,
        user_id=payer_id,
        amount=expense_data.amount,
        currency_id=expense_data.currency_id,
        description=expense_data.description,
        expense_date=expense_data.expense_date,
        is_big_expense=is_big_expense,
        split_only=expense_data.split_only
    )
    db.add(expense)
    await db.flush()

    # Add splits if provided
    if expense_data.splits:
        split_user_ids = {int(s.user_id) for s in expense_data.splits}
        # Ensure all split users are within the same family (and exist)
        split_users_result = await db.execute(
            select(User.id).where(
                User.id.in_(list(split_user_ids)),
                User.family_id == current_user.family_id
            )
        )
        valid_split_ids = {int(r[0]) for r in split_users_result.all()}
        invalid_split_ids = sorted(split_user_ids - valid_split_ids)
        if invalid_split_ids:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"分摊成员不存在或不在家庭中: {invalid_split_ids}"
            )

        for split_data in expense_data.splits:
            split = ExpenseSplit(
                expense_id=expense.id,
                user_id=split_data.user_id,
                share_amount=split_data.share_amount,
                share_percentage=split_data.share_percentage
            )
            db.add(split)

    await db.flush()
    await db.refresh(expense)

    # Load splits
    result = await db.execute(
        select(Expense)
        .options(selectinload(Expense.splits))
        .where(Expense.id == expense.id)
    )
    expense = result.scalar_one()

    # Rebuild expense-derived diamond spend (level progression).
    # This is a critical invariant for normal expenses: if it fails, the request must fail
    # so the DB transaction rolls back (no "half-created" expense rows).
    if not expense.split_only:
        await rebuild_expense_diamond_spends(db, expense)

    # For split-only records: allocate cost to split participants (and not the payer)
    if expense.split_only:
        # Critical invariant for split-only expenses: allocations must be generated.
        # If this fails, we must raise so the transaction rolls back.
        await sync_split_only_allocations(db, expense.id)

    # 清除支出趋势缓存
    await invalidate_family_expense_cache(current_user.family_id)

    resp = ExpenseResponse.model_validate(expense)
    if should_compute_big_pool:
        totals = await _get_big_expense_totals(db, current_user.family_id)
        resp.big_expense_balance = totals["balance_total"]
        resp.big_expense_balance_before = balance_before
        # 透支定义：新增支出后结余小于0
        resp.big_expense_overdrawn = totals["balance_total"] < 0

    return SuccessResponse(
        data=resp,
        message="支出记录创建成功"
    )


@router.get("/{expense_id}", response_model=SuccessResponse[ExpenseResponse])
async def get_expense(
    expense_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific expense"""
    if not current_user.family_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="You are not in a family")

    result = await db.execute(
        select(Expense)
        .options(selectinload(Expense.splits))
        .where(
            Expense.id == expense_id,
            Expense.family_id == current_user.family_id
        )
    )
    expense = result.scalar_one_or_none()

    if not expense:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Expense not found")

    # Prevent editing derived allocation expenses directly
    if getattr(expense, "allocation_source_id", None):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该记录为均摊生成记录，请修改原始分摊记录",
        )

    return SuccessResponse(
        data=ExpenseResponse.model_validate(expense),
        message="获取成功"
    )


@router.put("/{expense_id}", response_model=SuccessResponse[ExpenseResponse])
async def update_expense(
    expense_id: int,
    expense_data: ExpenseUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update an expense"""
    if not current_user.family_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="You are not in a family")

    result = await db.execute(
        select(Expense)
        .options(selectinload(Expense.splits))
        .where(
            Expense.id == expense_id,
            Expense.family_id == current_user.family_id
        )
    )
    expense = result.scalar_one_or_none()

    if not expense:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Expense not found")

    # Prevent editing derived allocation expenses directly
    if getattr(expense, "allocation_source_id", None):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该记录为均摊生成记录，请修改原始分摊记录",
        )

    was_split_only = bool(expense.split_only)
    was_big_expense = bool(expense.is_big_expense)

    # Optimistic locking (只有当明确传入version时才进行校验)
    if expense_data.version is not None and expense.version != expense_data.version:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="数据已被修改，请刷新后重试"
        )

    if expense_data.split_only is True and len(expense.splits or []) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="仅分摊支出需要先设置分摊成员"
        )

    # Determine category and big expense flag
    target_category_id = expense_data.category_id if expense_data.category_id is not None else expense.category_id
    category_flag = None
    if expense_data.category_id is not None:
        category_result = await db.execute(
            select(ExpenseCategory).where(
                ExpenseCategory.id == target_category_id,
                ExpenseCategory.family_id == current_user.family_id
            )
        )
        category = category_result.scalar_one_or_none()
        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="分类不存在")
        category_flag = bool(category.is_big_expense)

    # Validate currency exists if changing currency_id
    if expense_data.currency_id is not None:
        currency_exists = await db.scalar(
            select(exists().where(Currency.id == expense_data.currency_id))
        )
        if not currency_exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="货币不存在"
            )

    # Validate new user if provided
    if expense_data.user_id is not None:
        user_result = await db.execute(
            select(User).where(
                User.id == expense_data.user_id,
                User.family_id == current_user.family_id
            )
        )
        target_user = user_result.scalar_one_or_none()
        if not target_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="付款人不存在或不在家庭中")
        expense.user_id = expense_data.user_id

    # Update fields
    update_data = expense_data.model_dump(
        exclude_unset=True, exclude={"version", "user_id"})
    for key, value in update_data.items():
        setattr(expense, key, value)

    # Final is_big_expense flag (explicit > category > existing)
    if expense_data.is_big_expense is not None:
        expense.is_big_expense = expense_data.is_big_expense
    elif category_flag is not None:
        expense.is_big_expense = category_flag

    # Only recompute big-expense pool if this update can affect it.
    should_compute_big_pool = bool(was_big_expense or expense.is_big_expense)
    balance_before: Optional[float] = None
    if should_compute_big_pool:
        totals_before = await _get_big_expense_totals(db, current_user.family_id)
        balance_before = totals_before["balance_total"]
    expense.version += 1

    await db.flush()
    await db.refresh(expense)

    # Reload with splits to avoid async lazy loading during spend rebuild
    result = await db.execute(
        select(Expense)
        .options(selectinload(Expense.splits))
        .where(
            Expense.id == expense.id,
            Expense.family_id == current_user.family_id,
        )
    )
    expense = result.scalar_one()

    # Keep split-only and diamond spend states consistent after update.
    if expense.split_only:
        # split_only source itself should never count as direct spend
        await delete_expense_diamond_spends(db, int(expense.id))
        await sync_split_only_allocations(db, expense.id)
    else:
        # When toggled from split_only -> normal, cleanup old derived rows first.
        if was_split_only:
            await delete_split_only_allocations(db, int(expense.id))
        await rebuild_expense_diamond_spends(db, expense)

    # 清除支出趋势缓存
    await invalidate_family_expense_cache(current_user.family_id)

    resp = ExpenseResponse.model_validate(expense)
    if should_compute_big_pool:
        totals = await _get_big_expense_totals(db, current_user.family_id)
        resp.big_expense_balance = totals["balance_total"]
        resp.big_expense_balance_before = balance_before
        # 透支定义：更新后结余小于0
        resp.big_expense_overdrawn = totals["balance_total"] < 0

    return SuccessResponse(
        data=resp,
        message="支出记录已更新"
    )


@router.delete("/{expense_id}", response_model=SuccessResponse[dict])
async def delete_expense(
    expense_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete an expense"""
    if not current_user.family_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="You are not in a family")

    result = await db.execute(
        select(Expense).where(
            Expense.id == expense_id,
            Expense.family_id == current_user.family_id
        )
    )
    expense = result.scalar_one_or_none()

    if not expense:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Expense not found")

    # If deleting a derived allocation, delete the entire split-only source record instead.
    if getattr(expense, "allocation_source_id", None):
        expense_id = int(expense.allocation_source_id)
        result = await db.execute(
            select(Expense).where(
                Expense.id == expense_id,
                Expense.family_id == current_user.family_id,
            )
        )
        expense = result.scalar_one_or_none()
        if not expense:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Expense not found")

    # Remove derived allocation expenses (if any)
    if getattr(expense, "split_only", False):
        await delete_split_only_allocations(db, int(expense.id))

    # Remove expense-derived diamond spend (level progression)
    await delete_expense_diamond_spends(db, int(expense.id))

    await db.delete(expense)

    # 清除支出趋势缓存
    await invalidate_family_expense_cache(current_user.family_id)

    return SuccessResponse(data={}, message="支出记录已删除")


# ============== Splits ==============

@router.post("/{expense_id}/splits", response_model=SuccessResponse[List[ExpenseSplitResponse]])
async def set_expense_splits(
    expense_id: int,
    splits: List[ExpenseSplitCreate],
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Set expense splits"""
    if not current_user.family_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="You are not in a family")

    result = await db.execute(
        select(Expense)
        .options(selectinload(Expense.splits))
        .where(
            Expense.id == expense_id,
            Expense.family_id == current_user.family_id
        )
    )
    expense = result.scalar_one_or_none()

    if not expense:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Expense not found")

    # Prevent modifying derived allocation expenses directly
    if getattr(expense, "allocation_source_id", None):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该记录为均摊生成记录，请修改原始分摊记录",
        )

    if expense.split_only and len(splits) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="仅分摊支出需要至少一个分摊成员",
        )

    if splits:
        split_user_ids = {int(s.user_id) for s in splits}
        split_users_result = await db.execute(
            select(User.id).where(
                User.id.in_(list(split_user_ids)),
                User.family_id == current_user.family_id
            )
        )
        valid_split_ids = {int(r[0]) for r in split_users_result.all()}
        invalid_split_ids = sorted(split_user_ids - valid_split_ids)
        if invalid_split_ids:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"分摊成员不存在或不在家庭中: {invalid_split_ids}"
            )

    # Delete existing splits
    for split in expense.splits:
        await db.delete(split)

    # Add new splits
    new_splits = []
    for split_data in splits:
        split = ExpenseSplit(
            expense_id=expense.id,
            user_id=split_data.user_id,
            share_amount=split_data.share_amount,
            share_percentage=split_data.share_percentage
        )
        db.add(split)
        new_splits.append(split)

    await db.flush()
    for split in new_splits:
        await db.refresh(split)

    # Reload expense with updated splits, then rebuild/sync derived spend states
    result = await db.execute(
        select(Expense)
        .options(selectinload(Expense.splits))
        .where(
            Expense.id == expense.id,
            Expense.family_id == current_user.family_id,
        )
    )
    expense = result.scalar_one()
    if expense.split_only:
        await delete_expense_diamond_spends(db, int(expense.id))
        await sync_split_only_allocations(db, expense.id)
    else:
        await rebuild_expense_diamond_spends(db, expense)
    await invalidate_family_expense_cache(int(current_user.family_id))

    return SuccessResponse(
        data=[ExpenseSplitResponse.model_validate(s) for s in new_splits],
        message="费用分摊已设置"
    )


@router.patch("/splits/{split_id}/pay", response_model=SuccessResponse[ExpenseSplitResponse])
async def mark_split_paid(
    split_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Mark a split as paid"""
    if not current_user.family_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="You are not in a family")

    result = await db.execute(
        select(ExpenseSplit)
        .join(Expense)
        .where(
            ExpenseSplit.id == split_id,
            Expense.family_id == current_user.family_id
        )
    )
    split = result.scalar_one_or_none()

    if not split:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Split not found")

    split.is_paid = True
    split.paid_at = datetime.utcnow()

    await db.flush()
    await db.refresh(split)
    await invalidate_family_expense_cache(int(current_user.family_id))

    return SuccessResponse(
        data=ExpenseSplitResponse.model_validate(split),
        message="已标记为已支付"
    )


# ============== Statistics ==============

@router.get("/stats/monthly", response_model=SuccessResponse[MonthlyStats])
async def get_monthly_stats(
    year: int,
    month: int,
    user_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get monthly expense statistics"""
    if not current_user.family_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="You are not in a family")

    family_id = int(current_user.family_id)
    cache_key = f"expense:stats:family:{family_id}:monthly:{year:04d}-{month:02d}:user:{user_id or 'all'}"
    cached = await cache.get(cache_key)
    if cached is not None:
        return SuccessResponse(data=MonthlyStats(**cached), message="获取成功")

    month_start = date(year, month, 1)
    next_month = _next_month_start(month_start)

    # Calculate totals (USD-based)
    rate_cache: dict[date, dict[int, float]] = {}
    total_expense = 0.0
    level_totals = {
        "essential": 0.0,
        "supplementary": 0.0,
        "optional": 0.0,
    }

    category_totals: dict[str, float] = {}
    expense_rows = (
        await db.execute(
            select(
                ExpenseCategory.name,
                ExpenseCategory.type,
                Expense.currency_id,
                Expense.expense_date,
                func.sum(Expense.amount).label("amount_sum"),
            )
            .select_from(Expense)
            .outerjoin(ExpenseCategory, ExpenseCategory.id == Expense.category_id)
            .where(
                Expense.family_id == family_id,
                Expense.split_only == False,
                Expense.allocation_source_id.is_(None),
                *([Expense.user_id == user_id] if user_id else []),
                Expense.expense_date >= month_start,
                Expense.expense_date < next_month,
            )
            .group_by(
                ExpenseCategory.name,
                ExpenseCategory.type,
                Expense.currency_id,
                Expense.expense_date,
            )
        )
    ).all()

    for cat_name, cat_type, currency_id, expense_date, amount_sum in expense_rows:
        amount = float(amount_sum or 0)
        if amount <= 0:
            continue
        usd_amount = await convert_to_usd(
            db, amount, int(currency_id), expense_date, rate_cache
        )
        safe_cat_name = cat_name or "未分类"
        category_totals[safe_cat_name] = category_totals.get(safe_cat_name, 0.0) + usd_amount

        # Aggregate by level/type for front-end breakdown
        if cat_type == "fixed":
            level_totals["essential"] += usd_amount
        elif cat_type == "supplementary":
            level_totals["supplementary"] += usd_amount
        else:
            level_totals["optional"] += usd_amount

        total_expense += usd_amount

    # Get income for the month
    income_rows = (
        await db.execute(
            select(
                Income.currency_id,
                Income.income_date,
                func.sum(Income.amount).label("amount_sum"),
            )
            .where(
                Income.family_id == family_id,
                *([Income.user_id == user_id] if user_id else []),
                Income.income_date >= month_start,
                Income.income_date < next_month,
            )
            .group_by(
                Income.currency_id,
                Income.income_date,
            )
        )
    ).all()
    total_income = 0.0
    for currency_id, income_date, amount_sum in income_rows:
        amount = float(amount_sum or 0)
        if amount <= 0:
            continue
        total_income += await convert_to_usd(
            db, amount, int(currency_id), income_date, rate_cache
        )

    totals = await _get_big_expense_totals(db, family_id, year, month)
    month_reserved = totals["reserved_month"] or 0
    month_big_expense_spent = totals["expense_month"] or 0
    balance_month = totals["balance_month"] if totals["balance_month"] is not None else (
        month_reserved - month_big_expense_spent)
    balance_total = totals["balance_total"]

    payload = MonthlyStats(
        year=year,
        month=month,
        total_expense=total_expense,
        total_income=total_income,
        balance=total_income - total_expense,
        expense_by_category=category_totals,
        essential_expense=level_totals["essential"],
        supplementary_expense=level_totals["supplementary"],
        optional_expense=level_totals["optional"],
        big_expense_reserved=month_reserved,
        big_expense_expense=month_big_expense_spent,
        # 月度视角的余额
        big_expense_balance=balance_month,
        big_expense_balance_total=balance_total,
        big_expense_balance_month=balance_month
    )
    await cache.set(cache_key, payload.model_dump(), ttl_seconds=120)

    return SuccessResponse(
        data=payload,
        message="获取成功"
    )


@router.get("/stats/splits/settlements", response_model=SuccessResponse[List[SplitSettlement]])
async def get_split_settlements(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Aggregate all shared expenses and return net settlements between members."""
    if not current_user.family_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="You are not in a family")

    family_id = int(current_user.family_id)
    cache_key = f"expense:stats:family:{family_id}:splits:settlements"
    cached = await cache.get(cache_key)
    if cached is not None:
        return SuccessResponse(
            data=[SplitSettlement(**item) for item in cached],
            message="分摊结算计算成功"
        )

    rows = (
        await db.execute(
            select(
                ExpenseSplit.user_id,
                Expense.user_id,
                Expense.currency_id,
                Expense.expense_date,
                func.sum(ExpenseSplit.share_amount).label("share_sum"),
            )
            .join(Expense, Expense.id == ExpenseSplit.expense_id)
            .where(
                Expense.family_id == family_id,
                ExpenseSplit.is_paid == False
            )
            .group_by(
                ExpenseSplit.user_id,
                Expense.user_id,
                Expense.currency_id,
                Expense.expense_date,
            )
        )
    ).all()
    ledger: dict[tuple[int, int], float] = {}
    rate_cache: dict[date, dict[int, float]] = {}

    for debtor_id_raw, payer_id_raw, currency_id, expense_date, share_sum in rows:
        debtor_id = int(debtor_id_raw)
        payer_id = int(payer_id_raw)
        if debtor_id == payer_id:
            continue

        amount = float(share_sum or 0)
        if amount <= 0:
            continue

        amount = await convert_to_usd(
            db, amount, int(currency_id), expense_date, rate_cache
        )

        key = (debtor_id, payer_id)
        ledger[key] = ledger.get(key, 0) + amount

    settlements: List[SplitSettlement] = []
    processed_pairs = set()

    for (debtor_id, payer_id), amount in ledger.items():
        pair_key = tuple(sorted((debtor_id, payer_id)))
        if pair_key in processed_pairs:
            continue

        reverse_amount = ledger.get((payer_id, debtor_id), 0)
        net_amount = amount - reverse_amount

        if net_amount > 0:
            settlements.append(SplitSettlement(
                from_user_id=debtor_id,
                to_user_id=payer_id,
                amount=round(net_amount, 2)
            ))
        elif net_amount < 0:
            settlements.append(SplitSettlement(
                from_user_id=payer_id,
                to_user_id=debtor_id,
                amount=round(-net_amount, 2)
            ))

        processed_pairs.add(pair_key)

    await cache.set(
        cache_key,
        [item.model_dump() for item in settlements],
        ttl_seconds=60,
    )

    return SuccessResponse(
        data=settlements,
        message="分摊结算计算成功"
    )


@router.post("/splits/settle-all", response_model=SuccessResponse[dict])
async def settle_all_splits(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Mark all unpaid splits as paid (clear current settlement cycle)."""
    if not current_user.family_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="You are not in a family")

    result = await db.execute(
        select(ExpenseSplit)
        .join(Expense)
        .where(
            Expense.family_id == current_user.family_id,
            ExpenseSplit.is_paid == False
        )
    )
    splits = result.scalars().all()

    for split in splits:
        split.is_paid = True
        split.paid_at = datetime.utcnow()

    await db.commit()
    await invalidate_family_expense_cache(int(current_user.family_id))

    return SuccessResponse(
        data={"settled_count": len(splits)},
        message="已清帐"
    )


@router.get("/budgets/big-expense", response_model=SuccessResponse[BigExpenseBudgetSummary])
async def get_big_expense_budget(
    months: int = Query(6, ge=1, le=12),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get big expense budget summary and monthly history."""
    if not current_user.family_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="You are not in a family")

    family_id = int(current_user.family_id)
    cache_key = f"expense:stats:family:{family_id}:big-expense-budget:months:{months}"
    cached = await cache.get(cache_key)
    if cached is not None:
        return SuccessResponse(data=BigExpenseBudgetSummary(**cached), message="获取成功")

    totals = await _get_big_expense_totals(db, family_id)

    today_month_start = date.today().replace(day=1)
    window_start = _add_months(today_month_start, -(months - 1))
    window_end = _next_month_start(today_month_start)

    rate_cache: dict[date, dict[int, float]] = {}
    reserved_by_month: dict[tuple[int, int], float] = {}
    spent_by_month: dict[tuple[int, int], float] = {}

    income_rows = (
        await db.execute(
            select(
                Income.currency_id,
                Income.income_date,
                func.sum(Income.big_expense_reserved).label("reserved_sum"),
            )
            .where(
                Income.family_id == family_id,
                Income.big_expense_reserved > 0,
                Income.income_date >= window_start,
                Income.income_date < window_end,
            )
            .group_by(
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
        key = (income_date.year, income_date.month)
        reserved_by_month[key] = reserved_by_month.get(key, 0.0) + usd_reserved

    expense_rows = (
        await db.execute(
            select(
                Expense.currency_id,
                Expense.expense_date,
                func.sum(Expense.amount).label("amount_sum"),
            )
            .where(
                Expense.family_id == family_id,
                Expense.is_big_expense == True,
                Expense.split_only == False,
                Expense.allocation_source_id.is_(None),
                Expense.amount > 0,
                Expense.expense_date >= window_start,
                Expense.expense_date < window_end,
            )
            .group_by(
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
        key = (expense_date.year, expense_date.month)
        spent_by_month[key] = spent_by_month.get(key, 0.0) + usd_amount

    # Build history from oldest to newest
    history_items: list[BigExpenseHistoryItem] = []
    for offset in range(-(months - 1), 1):
        target_month = _add_months(today_month_start, offset)
        key = (target_month.year, target_month.month)
        month_reserved = reserved_by_month.get(key, 0.0)
        month_spent = spent_by_month.get(key, 0.0)
        history_items.append(BigExpenseHistoryItem(
            year=target_month.year,
            month=target_month.month,
            reserved=month_reserved,
            spent=month_spent,
            balance_month=month_reserved - month_spent
        ))

    summary = BigExpenseBudgetSummary(
        balance_total=totals["balance_total"],
        overdrawn=totals["balance_total"] < 0,
        history=history_items
    )
    await cache.set(cache_key, summary.model_dump(), ttl_seconds=300)

    return SuccessResponse(data=summary, message="获取成功")


@router.get("/stats/category", response_model=SuccessResponse[List[CategoryStats]])
async def get_category_stats(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    user_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get expense statistics by category"""
    if not current_user.family_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="You are not in a family")

    family_id = int(current_user.family_id)
    cache_key = (
        f"expense:stats:family:{family_id}:category:"
        f"start:{start_date or 'none'}:end:{end_date or 'none'}:user:{user_id or 'all'}"
    )
    cached = await cache.get(cache_key)
    if cached is not None:
        return SuccessResponse(
            data=[CategoryStats(**item) for item in cached],
            message="获取成功",
        )

    query = (
        select(
            Expense.category_id,
            ExpenseCategory.name,
            Expense.currency_id,
            Expense.expense_date,
            func.sum(Expense.amount).label("amount_sum"),
            func.count(Expense.id).label("item_count"),
        )
        .select_from(Expense)
        .outerjoin(ExpenseCategory, ExpenseCategory.id == Expense.category_id)
        .where(
            Expense.family_id == family_id,
            Expense.split_only == False,
            Expense.allocation_source_id.is_(None),
            Expense.amount > 0,
        )
    )

    if start_date:
        query = query.where(Expense.expense_date >= start_date)
    if end_date:
        query = query.where(Expense.expense_date <= end_date)
    if user_id:
        query = query.where(Expense.user_id == user_id)

    query = query.group_by(
        Expense.category_id,
        ExpenseCategory.name,
        Expense.currency_id,
        Expense.expense_date,
    )
    rows = (await db.execute(query)).all()

    # Calculate totals by category
    category_totals: dict[int, dict] = {}
    total_amount = 0.0
    rate_cache: dict[date, dict[int, float]] = {}

    for cat_id_raw, cat_name_raw, currency_id, expense_date, amount_sum, item_count in rows:
        # 使用 0 表示未分类，避免 None 作为字典键
        cat_id = int(cat_id_raw) if cat_id_raw is not None else 0
        cat_name = cat_name_raw or "未分类"
        amount = float(amount_sum or 0)
        if amount <= 0:
            continue
        amount = await convert_to_usd(
            db, amount, int(currency_id), expense_date, rate_cache
        )

        if cat_id not in category_totals:
            category_totals[cat_id] = {
                "name": cat_name, "total": 0, "count": 0}

        category_totals[cat_id]["total"] += amount
        category_totals[cat_id]["count"] += int(item_count or 0)
        total_amount += amount

    # Build response
    stats: list[CategoryStats] = []
    for cat_id, data in category_totals.items():
        percentage = (data["total"] / total_amount *
                      100) if total_amount > 0 else 0
        stats.append(CategoryStats(
            category_id=cat_id if cat_id != 0 else None,  # 0 转回 None 表示未分类
            category_name=data["name"],
            total_amount=data["total"],
            percentage=round(percentage, 2),
            count=data["count"]
        ))

    # Sort by total amount descending
    stats.sort(key=lambda x: x.total_amount, reverse=True)
    await cache.set(
        cache_key,
        [item.model_dump() for item in stats],
        ttl_seconds=120,
    )

    return SuccessResponse(data=stats, message="获取成功")


@router.get("/stats/monthly-trend")
async def get_monthly_trend(
    months: int = Query(default=6, ge=1, le=24),
    user_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取最近N个月的支出趋势

    Args:
        months: 要查询的月份数量，默认6个月，最多24个月

    Returns:
        按月份排序的支出总额列表

    Note:
        结果会缓存1小时，新增/修改/删除支出时会自动清除缓存
    """
    if not current_user.family_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="请先加入家庭"
        )

    today = date.today()

    # 生成缓存键: expense:trend:family:{family_id}:user:{user_id|all}:months:{months}:date:{today}
    cache_key = f"expense:trend:family:{current_user.family_id}:user:{user_id or 'all'}:months:{months}:date:{today}"

    # 尝试从缓存获取
    cached_result = await cache.get(cache_key)
    if cached_result is not None:
        return SuccessResponse(
            data=cached_result,
            message="获取趋势数据成功"
        )

    # 缓存未命中，查询数据库（单次聚合查询 + 换算）
    month_start = today.replace(day=1)
    window_start = _add_months(month_start, -(months - 1))
    window_end = _next_month_start(month_start)

    month_totals: dict[tuple[int, int], float] = {}
    rate_cache: dict[date, dict[int, float]] = {}
    rows = (
        await db.execute(
            select(
                Expense.currency_id,
                Expense.expense_date,
                func.sum(Expense.amount).label("amount_sum"),
            ).where(
                Expense.family_id == current_user.family_id,
                Expense.split_only == False,
                Expense.allocation_source_id.is_(None),
                Expense.amount > 0,
                *([Expense.user_id == user_id] if user_id else []),
                Expense.expense_date >= window_start,
                Expense.expense_date < window_end,
            ).group_by(
                Expense.currency_id,
                Expense.expense_date,
            )
        )
    ).all()

    for currency_id, expense_date, amount_sum in rows:
        amount = float(amount_sum or 0)
        if amount <= 0:
            continue
        usd_amount = await convert_to_usd(
            db, amount, int(currency_id), expense_date, rate_cache
        )
        key = (expense_date.year, expense_date.month)
        month_totals[key] = month_totals.get(key, 0.0) + usd_amount

    results = []
    for offset in range(-(months - 1), 1):
        target = _add_months(month_start, offset)
        key = (target.year, target.month)
        results.append({
            "year": target.year,
            "month": target.month,
            "label": f"{target.month}月",
            "total": float(month_totals.get(key, 0.0)),
        })

    # 缓存结果，1小时过期
    await cache.set(cache_key, results, ttl_seconds=3600)

    return SuccessResponse(
        data=results,
        message="获取趋势数据成功"
    )
