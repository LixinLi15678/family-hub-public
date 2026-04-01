"""
Family schemas
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class FamilyCreate(BaseModel):
    """Schema for creating a family"""
    name: str = Field(..., min_length=1, max_length=100)


class FamilyJoin(BaseModel):
    """Schema for joining a family"""
    invite_code: str = Field(..., min_length=8, max_length=8)


class FamilyMemberResponse(BaseModel):
    """Schema for family member info"""
    id: int
    username: str
    email: str
    avatar_url: Optional[str] = None
    points_balance: int = 0
    points_spent_total: int = 0
    role: str

    class Config:
        from_attributes = True


class FamilyResponse(BaseModel):
    """Schema for family response"""
    id: int
    name: str
    invite_code: str
    created_at: datetime
    members: Optional[List[FamilyMemberResponse]] = None

    class Config:
        from_attributes = True
