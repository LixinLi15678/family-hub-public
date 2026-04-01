"""
Chore and points routes
"""
from datetime import datetime, date
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.models.chore import Chore, ChoreCompletion, PointTransaction
from app.schemas.chore import (
    ChoreCreate, ChoreUpdate, ChoreResponse,
    ChoreCompletionResponse, PointTransactionResponse,
    UserBriefResponse
)
from app.schemas.common import SuccessResponse, PaginatedResponse, PaginatedData
from app.utils.security import get_current_user

router = APIRouter(prefix="/chores", tags=["Chores"])


def build_chore_response(chore: Chore) -> ChoreResponse:
    """Build ChoreResponse with related user objects"""
    response = ChoreResponse.model_validate(chore)
    
    # Add assigned_to_user if available
    if chore.assigned_user:
        response.assigned_to_user = UserBriefResponse.model_validate(chore.assigned_user)
    
    # Add created_by_user if available
    if chore.created_by_user:
        response.created_by_user = UserBriefResponse.model_validate(chore.created_by_user)
    
    return response


def build_completion_response(completion: ChoreCompletion) -> ChoreCompletionResponse:
    """Build ChoreCompletionResponse with related objects"""
    response = ChoreCompletionResponse.model_validate(completion)
    
    # Add chore if available
    if completion.chore:
        response.chore = build_chore_response(completion.chore)
    
    # Add completed_by_user if available
    if completion.completed_by_user:
        response.completed_by_user = UserBriefResponse.model_validate(completion.completed_by_user)
    
    # Add verified_by_user if available
    if completion.verified_by_user:
        response.verified_by_user = UserBriefResponse.model_validate(completion.verified_by_user)
    
    return response


@router.get("", response_model=SuccessResponse[List[ChoreResponse]])
async def get_chores(
    is_active: Optional[bool] = True,
    assigned_to: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all chores for the family"""
    if not current_user.family_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You are not in a family")
    
    query = (
        select(Chore)
        .options(
            selectinload(Chore.assigned_user),
            selectinload(Chore.created_by_user)
        )
        .where(Chore.family_id == current_user.family_id)
    )
    
    if is_active is not None:
        query = query.where(Chore.is_active == is_active)
    if assigned_to:
        query = query.where(Chore.assigned_to == assigned_to)
    
    query = query.order_by(Chore.due_date, Chore.created_at.desc())
    
    result = await db.execute(query)
    chores = result.scalars().all()
    
    return SuccessResponse(
        data=[build_chore_response(c) for c in chores],
        message="获取成功"
    )


@router.post("", response_model=SuccessResponse[ChoreResponse])
async def create_chore(
    chore_data: ChoreCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new chore"""
    if not current_user.family_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You are not in a family")
    
    chore = Chore(
        family_id=current_user.family_id,
        name=chore_data.name,
        description=chore_data.description,
        points_reward=chore_data.points_reward,
        assigned_to=chore_data.assigned_to,
        created_by=current_user.id,
        recurrence=chore_data.recurrence,
        repeat_days=chore_data.repeat_days,
        due_date=chore_data.due_date
    )
    db.add(chore)
    await db.flush()
    
    # Reload with relationships
    result = await db.execute(
        select(Chore)
        .options(
            selectinload(Chore.assigned_user),
            selectinload(Chore.created_by_user)
        )
        .where(Chore.id == chore.id)
    )
    chore = result.scalar_one()
    
    return SuccessResponse(
        data=build_chore_response(chore),
        message="家务任务创建成功"
    )


@router.put("/{chore_id}", response_model=SuccessResponse[ChoreResponse])
async def update_chore(
    chore_id: int,
    chore_data: ChoreUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a chore"""
    if not current_user.family_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You are not in a family")
    
    result = await db.execute(
        select(Chore)
        .options(
            selectinload(Chore.assigned_user),
            selectinload(Chore.created_by_user)
        )
        .where(
            Chore.id == chore_id,
            Chore.family_id == current_user.family_id
        )
    )
    chore = result.scalar_one_or_none()
    
    if not chore:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chore not found")
    
    # Update fields
    update_data = chore_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(chore, key, value)
    
    await db.flush()
    
    # Reload with relationships (in case assigned_to changed)
    result = await db.execute(
        select(Chore)
        .options(
            selectinload(Chore.assigned_user),
            selectinload(Chore.created_by_user)
        )
        .where(Chore.id == chore.id)
    )
    chore = result.scalar_one()
    
    return SuccessResponse(
        data=build_chore_response(chore),
        message="家务任务已更新"
    )


@router.delete("/{chore_id}", response_model=SuccessResponse[dict])
async def delete_chore(
    chore_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a chore"""
    if not current_user.family_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You are not in a family")
    
    result = await db.execute(
        select(Chore).where(
            Chore.id == chore_id,
            Chore.family_id == current_user.family_id
        )
    )
    chore = result.scalar_one_or_none()
    
    if not chore:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chore not found")
    
    await db.delete(chore)
    
    return SuccessResponse(data={}, message="家务任务已删除")


@router.post("/{chore_id}/complete", response_model=SuccessResponse[ChoreCompletionResponse])
async def complete_chore(
    chore_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Complete a chore and earn points"""
    if not current_user.family_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You are not in a family")
    
    result = await db.execute(
        select(Chore)
        .options(
            selectinload(Chore.assigned_user),
            selectinload(Chore.created_by_user)
        )
        .where(
            Chore.id == chore_id,
            Chore.family_id == current_user.family_id
        )
    )
    chore = result.scalar_one_or_none()
    
    if not chore:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chore not found")
    
    if not chore.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Chore is not active")
    
    # Determine who receives points:
    # - 如果任务指定了负责人，钻石和完成者归属指派的人
    # - 如果未指定，钻石给实际点击完成的用户
    award_user = chore.assigned_user if chore.assigned_user else current_user
    if chore.assigned_to and not chore.assigned_user:
        # Load assigned user if not already loaded
        user_result = await db.execute(select(User).where(User.id == chore.assigned_to))
        award_user = user_result.scalar_one_or_none() or current_user
    
    # 防重复提交：检查是否已在限定时间内完成过
    from datetime import date as date_type
    today = date_type.today()
    
    if chore.recurrence == 'daily':
        # daily任务：每天只能完成一次
        existing = await db.execute(
            select(ChoreCompletion).where(
                ChoreCompletion.chore_id == chore_id,
                ChoreCompletion.completed_by == current_user.id,
                func.date(ChoreCompletion.completed_at) == today
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="今天已完成过该任务"
            )
    elif chore.recurrence == 'weekly':
        # weekly任务：每周只能完成一次（同一天内防重复）
        existing = await db.execute(
            select(ChoreCompletion).where(
                ChoreCompletion.chore_id == chore_id,
                ChoreCompletion.completed_by == current_user.id,
                func.date(ChoreCompletion.completed_at) == today
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="今天已完成过该任务"
            )
    elif chore.recurrence == 'once':
        # once任务：只能完成一次
        existing = await db.execute(
            select(ChoreCompletion).where(
                ChoreCompletion.chore_id == chore_id
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="该任务已完成"
            )
    
    # Create completion record
    completion = ChoreCompletion(
        chore_id=chore.id,
        completed_by=award_user.id,
        points_earned=chore.points_reward
    )
    db.add(completion)
    await db.flush()
    
    # Add points to award user
    award_user.points_balance += chore.points_reward
    
    # Create point transaction
    transaction = PointTransaction(
        user_id=award_user.id,
        amount=chore.points_reward,
        type="chore",
        reference_id=completion.id,
        balance_after=award_user.points_balance,
        description=f"完成家务: {chore.name}"
    )
    db.add(transaction)
    
    # If it's a one-time chore, mark as inactive
    if chore.recurrence == "once":
        chore.is_active = False
    
    await db.flush()
    
    # Reload completion with all relationships
    result = await db.execute(
        select(ChoreCompletion)
        .options(
            selectinload(ChoreCompletion.chore).selectinload(Chore.assigned_user),
            selectinload(ChoreCompletion.chore).selectinload(Chore.created_by_user),
            selectinload(ChoreCompletion.completed_by_user)
        )
        .where(ChoreCompletion.id == completion.id)
    )
    completion = result.scalar_one()
    
    return SuccessResponse(
        data=build_completion_response(completion),
        message=f"家务完成！获得 {chore.points_reward} 钻石"
    )


@router.get("/history", response_model=PaginatedResponse[ChoreCompletionResponse])
async def get_chore_history(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user_id: Optional[int] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get chore completion history
    
    Args:
        page: 页码
        page_size: 每页数量
        user_id: 按用户筛选
        start_date: 开始日期 (包含)
        end_date: 结束日期 (包含)
    """
    if not current_user.family_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You are not in a family")
    
    # Base query with joins for counting
    base_query = (
        select(ChoreCompletion)
        .join(Chore)
        .where(Chore.family_id == current_user.family_id)
    )
    
    if user_id:
        base_query = base_query.where(ChoreCompletion.completed_by == user_id)
    
    # 日期筛选
    if start_date:
        base_query = base_query.where(func.date(ChoreCompletion.completed_at) >= start_date)
    if end_date:
        base_query = base_query.where(func.date(ChoreCompletion.completed_at) <= end_date)
    
    # Count total
    count_query = select(func.count()).select_from(base_query.subquery())
    total = (await db.execute(count_query)).scalar()
    
    # Get paginated results with all relationships
    query = (
        select(ChoreCompletion)
        .options(
            selectinload(ChoreCompletion.chore).selectinload(Chore.assigned_user),
            selectinload(ChoreCompletion.chore).selectinload(Chore.created_by_user),
            selectinload(ChoreCompletion.completed_by_user),
            selectinload(ChoreCompletion.verified_by_user)
        )
        .join(Chore)
        .where(Chore.family_id == current_user.family_id)
    )
    
    if user_id:
        query = query.where(ChoreCompletion.completed_by == user_id)
    
    # 日期筛选 (与计数查询保持一致)
    if start_date:
        query = query.where(func.date(ChoreCompletion.completed_at) >= start_date)
    if end_date:
        query = query.where(func.date(ChoreCompletion.completed_at) <= end_date)
    
    query = query.order_by(ChoreCompletion.completed_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    
    result = await db.execute(query)
    completions = result.scalars().all()
    
    return PaginatedResponse(
        data=PaginatedData(
            items=[build_completion_response(c) for c in completions],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=(total + page_size - 1) // page_size
        )
    )
