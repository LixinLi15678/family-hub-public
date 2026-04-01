"""
Todo schemas
"""
from datetime import datetime, date
from typing import Optional
from pydantic import BaseModel, Field

from app.schemas.chore import UserBriefResponse


class TodoCreate(BaseModel):
    """Schema for creating a todo"""
    title: str = Field(..., min_length=1, max_length=150)
    description: Optional[str] = None
    assigned_to: Optional[int] = None
    due_date: Optional[date] = None


class TodoUpdate(BaseModel):
    """Schema for updating a todo"""
    title: Optional[str] = Field(None, min_length=1, max_length=150)
    description: Optional[str] = None
    assigned_to: Optional[int] = None
    due_date: Optional[date] = None


class TodoResponse(BaseModel):
    """Schema for todo response"""
    id: int
    family_id: int
    title: str
    description: Optional[str] = None
    assigned_to: Optional[int] = None
    assigned_to_user: Optional[UserBriefResponse] = None
    created_by: int
    created_by_user: Optional[UserBriefResponse] = None
    due_date: Optional[date] = None
    is_completed: bool
    completed_at: Optional[datetime] = None
    completed_by: Optional[int] = None
    completed_by_user: Optional[UserBriefResponse] = None
    created_at: datetime

    class Config:
        from_attributes = True


class TodoCompleteResponse(BaseModel):
    """Schema for todo completion response"""
    todo: TodoResponse
    points_awarded: int
    awarded_to: int
