"""
Todo routes
"""
from datetime import datetime, date, time, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.models.todo import Todo
from app.models.chore import PointTransaction
from app.schemas.todo import TodoCreate, TodoUpdate, TodoResponse, TodoCompleteResponse
from app.schemas.chore import UserBriefResponse
from app.schemas.common import SuccessResponse
from app.utils.security import get_current_user

router = APIRouter(prefix="/todos", tags=["Todos"])


def build_todo_response(todo: Todo) -> TodoResponse:
    """Build TodoResponse with nested user info"""
    response = TodoResponse.model_validate(todo)

    if todo.assigned_user:
        response.assigned_to_user = UserBriefResponse.model_validate(todo.assigned_user)
    if todo.created_by_user:
        response.created_by_user = UserBriefResponse.model_validate(todo.created_by_user)
    if todo.completed_by_user:
        response.completed_by_user = UserBriefResponse.model_validate(todo.completed_by_user)

    return response


@router.get("", response_model=SuccessResponse[List[TodoResponse]])
async def get_todos(
    is_completed: Optional[bool] = None,
    limit: Optional[int] = Query(None, ge=1, le=100),
    completed_from: Optional[date] = None,
    completed_to: Optional[date] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all todos for the family"""
    if not current_user.family_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You are not in a family")

    query = (
        select(Todo)
        .options(
            selectinload(Todo.assigned_user),
            selectinload(Todo.created_by_user),
            selectinload(Todo.completed_by_user),
        )
        .where(Todo.family_id == current_user.family_id)
    )

    if is_completed is not None:
        query = query.where(Todo.is_completed == is_completed)

    if is_completed is True:
        if completed_from:
            query = query.where(Todo.completed_at >= datetime.combine(completed_from, time.min))
        if completed_to:
            query = query.where(Todo.completed_at < datetime.combine(completed_to + timedelta(days=1), time.min))

        # 最近完成优先
        query = query.order_by(
            Todo.completed_at.is_(None),
            Todo.completed_at.desc(),
            Todo.created_at.desc(),
        )
    else:
        # 有截止日期的优先，随后按截止日近到远，再按创建时间
        query = query.order_by(Todo.due_date.is_(None), Todo.due_date, Todo.created_at.desc())

    if limit is not None:
        query = query.limit(limit)

    result = await db.execute(query)
    todos = result.scalars().all()

    return SuccessResponse(
        data=[build_todo_response(todo) for todo in todos],
        message="获取成功"
    )


@router.post("", response_model=SuccessResponse[TodoResponse])
async def create_todo(
    todo_data: TodoCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a todo"""
    if not current_user.family_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You are not in a family")

    assigned_id = todo_data.assigned_to or current_user.id

    todo = Todo(
        family_id=current_user.family_id,
        title=todo_data.title,
        description=todo_data.description,
        assigned_to=assigned_id,
        created_by=current_user.id,
        due_date=todo_data.due_date,
    )
    db.add(todo)
    await db.flush()

    result = await db.execute(
        select(Todo)
        .options(
            selectinload(Todo.assigned_user),
            selectinload(Todo.created_by_user),
            selectinload(Todo.completed_by_user),
        )
        .where(Todo.id == todo.id)
    )
    todo = result.scalar_one()

    return SuccessResponse(
        data=build_todo_response(todo),
        message="待办创建成功"
    )


@router.get("/{todo_id}", response_model=SuccessResponse[TodoResponse])
async def get_todo(
    todo_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a single todo"""
    if not current_user.family_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You are not in a family")

    result = await db.execute(
        select(Todo)
        .options(
            selectinload(Todo.assigned_user),
            selectinload(Todo.created_by_user),
            selectinload(Todo.completed_by_user),
        )
        .where(
            Todo.id == todo_id,
            Todo.family_id == current_user.family_id,
        )
    )
    todo = result.scalar_one_or_none()

    if not todo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Todo not found")

    return SuccessResponse(
        data=build_todo_response(todo),
        message="获取成功"
    )


@router.put("/{todo_id}", response_model=SuccessResponse[TodoResponse])
async def update_todo(
    todo_id: int,
    todo_data: TodoUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a todo"""
    if not current_user.family_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You are not in a family")

    result = await db.execute(
        select(Todo)
        .options(
            selectinload(Todo.assigned_user),
            selectinload(Todo.created_by_user),
            selectinload(Todo.completed_by_user),
        )
        .where(
            Todo.id == todo_id,
            Todo.family_id == current_user.family_id,
        )
    )
    todo = result.scalar_one_or_none()

    if not todo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Todo not found")

    update_data = todo_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(todo, key, value)

    await db.flush()

    return SuccessResponse(
        data=build_todo_response(todo),
        message="待办已更新"
    )


@router.delete("/{todo_id}", response_model=SuccessResponse[dict])
async def delete_todo(
    todo_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a todo"""
    if not current_user.family_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You are not in a family")

    result = await db.execute(
        select(Todo).where(
            Todo.id == todo_id,
            Todo.family_id == current_user.family_id,
        )
    )
    todo = result.scalar_one_or_none()

    if not todo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Todo not found")

    await db.delete(todo)

    return SuccessResponse(data={}, message="待办已删除")


@router.post("/{todo_id}/complete", response_model=SuccessResponse[TodoCompleteResponse])
async def complete_todo(
    todo_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Mark todo as completed and award points"""
    if not current_user.family_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You are not in a family")

    result = await db.execute(
        select(Todo)
        .options(
            selectinload(Todo.assigned_user),
            selectinload(Todo.created_by_user),
            selectinload(Todo.completed_by_user),
        )
        .where(
            Todo.id == todo_id,
            Todo.family_id == current_user.family_id,
        )
    )
    todo = result.scalar_one_or_none()

    if not todo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Todo not found")
    if todo.is_completed:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Todo already completed")

    todo.is_completed = True
    todo.completed_at = datetime.utcnow()
    todo.completed_by = current_user.id

    # Award points to assignee (default: creator/current user)
    award_user = todo.assigned_user
    if not award_user and todo.assigned_to:
        user_res = await db.execute(select(User).where(User.id == todo.assigned_to))
        award_user = user_res.scalar_one_or_none()
    if not award_user:
        award_user = current_user

    award_user.points_balance += 5

    transaction = PointTransaction(
        user_id=award_user.id,
        amount=5,
        type="todo",
        reference_id=todo.id,
        balance_after=award_user.points_balance,
        description=f"完成待办: {todo.title}"
    )
    db.add(transaction)

    await db.flush()

    # Reload with relationships
    result = await db.execute(
        select(Todo)
        .options(
            selectinload(Todo.assigned_user),
            selectinload(Todo.created_by_user),
            selectinload(Todo.completed_by_user),
        )
        .where(Todo.id == todo_id)
    )
    todo = result.scalar_one()

    return SuccessResponse(
        data=TodoCompleteResponse(
            todo=build_todo_response(todo),
            points_awarded=5,
            awarded_to=award_user.id,
        ),
        message="待办已完成"
    )
