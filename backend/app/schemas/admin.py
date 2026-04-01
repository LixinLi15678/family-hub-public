"""
Schemas for admin management tools
"""
from datetime import datetime, date
from typing import Optional, List
from pydantic import BaseModel, Field


class AdminCouponResponse(BaseModel):
    id: int
    user_id: int
    name: str
    description: Optional[str] = None
    quantity: int
    expires_on: Optional[date] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AdminMemberResponse(BaseModel):
    user_id: int
    username: str
    email: str
    avatar_url: Optional[str] = None
    role: str
    points_balance: int
    points_spent_total: int
    coupons: List[AdminCouponResponse] = Field(default_factory=list)


class AdminOperationLogResponse(BaseModel):
    id: str
    op_type: str
    user_id: int
    username: str
    delta: int
    target: int
    reason: Optional[str] = None
    created_at: datetime


class AdminMemberCenterResponse(BaseModel):
    members: List[AdminMemberResponse]
    recent_operations: List[AdminOperationLogResponse]
    level_effect_tiers: List[dict]


class AdminSetBalanceRequest(BaseModel):
    target_balance: int = Field(..., ge=0)
    reason: Optional[str] = Field(None, max_length=255)


class AdminSetBalanceResponse(BaseModel):
    user_id: int
    previous_balance: int
    target_balance: int
    delta: int


class AdminSetExperienceRequest(BaseModel):
    target_spent_total: int = Field(..., ge=0)
    reason: Optional[str] = Field(None, max_length=255)


class AdminSetExperienceResponse(BaseModel):
    user_id: int
    previous_spent_total: int
    target_spent_total: int
    delta: int


class AdminCreateCouponRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=80)
    quantity: int = Field(1, ge=1, le=9999)
    description: Optional[str] = Field(None, max_length=255)
    expires_on: Optional[date] = None


class AdminDeleteCouponResponse(BaseModel):
    deleted: bool
    remaining_quantity: int
