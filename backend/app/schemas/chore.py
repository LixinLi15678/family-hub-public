"""
Chore and Points system schemas
"""
from datetime import datetime, date
from typing import Optional, List, TYPE_CHECKING
from pydantic import BaseModel, Field, field_validator, model_validator


# ============== Brief User Schema (for nested responses) ==============

class UserBriefResponse(BaseModel):
    """Brief user info for nested responses"""
    id: int
    username: str
    avatar_url: Optional[str] = None

    class Config:
        from_attributes = True


# ============== Chore Schemas ==============

class ChoreCreate(BaseModel):
    """Schema for creating a chore"""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    points_reward: int = Field(..., ge=1)
    assigned_to: Optional[int] = None
    recurrence: Optional[str] = Field(None, pattern="^(daily|weekly|monthly|once)$")
    repeat_days: Optional[List[int]] = None  # [0-6] for Sunday-Saturday, used when recurrence="weekly"
    due_date: Optional[date] = None
    
    @field_validator('repeat_days')
    @classmethod
    def validate_repeat_days_range(cls, v):
        """验证repeat_days值在0-6范围内"""
        if v is not None:
            if not all(isinstance(day, int) and 0 <= day <= 6 for day in v):
                raise ValueError('repeat_days 的每个值必须在 0-6 之间 (0=周日, 6=周六)')
            if len(v) != len(set(v)):
                raise ValueError('repeat_days 不能包含重复的值')
        return v
    
    @model_validator(mode='after')
    def validate_repeat_days_with_recurrence(self):
        """验证repeat_days只在weekly时有效"""
        if self.repeat_days and self.recurrence != 'weekly':
            raise ValueError('repeat_days 只在 recurrence 为 weekly 时有效')
        return self


class ChoreUpdate(BaseModel):
    """Schema for updating a chore"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    points_reward: Optional[int] = Field(None, ge=1)
    assigned_to: Optional[int] = None
    recurrence: Optional[str] = Field(None, pattern="^(daily|weekly|monthly|once)$")
    repeat_days: Optional[List[int]] = None
    due_date: Optional[date] = None
    is_active: Optional[bool] = None
    
    @field_validator('repeat_days')
    @classmethod
    def validate_repeat_days_range(cls, v):
        """验证repeat_days值在0-6范围内"""
        if v is not None:
            if not all(isinstance(day, int) and 0 <= day <= 6 for day in v):
                raise ValueError('repeat_days 的每个值必须在 0-6 之间 (0=周日, 6=周六)')
            if len(v) != len(set(v)):
                raise ValueError('repeat_days 不能包含重复的值')
        return v


class ChoreResponse(BaseModel):
    """Schema for chore response"""
    id: int
    family_id: int
    name: str
    description: Optional[str] = None
    points_reward: int
    assigned_to: Optional[int] = None
    assigned_to_user: Optional[UserBriefResponse] = None  # 关联的用户对象
    created_by: int
    created_by_user: Optional[UserBriefResponse] = None  # 创建者用户对象
    recurrence: Optional[str] = None
    repeat_days: Optional[List[int]] = None  # 周重复的星期几
    due_date: Optional[date] = None
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class ChoreCompletionResponse(BaseModel):
    """Schema for chore completion response"""
    id: int
    chore_id: int
    chore: Optional[ChoreResponse] = None  # 关联的家务对象
    completed_by: int
    completed_by_user: Optional[UserBriefResponse] = None  # 完成者用户对象
    points_earned: int
    completed_at: datetime
    verified_by: Optional[int] = None
    verified_by_user: Optional[UserBriefResponse] = None  # 验证者用户对象
    verified_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ============== Point Product Schemas ==============

class PointProductCreate(BaseModel):
    """Schema for creating a point product"""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    points_price: int = Field(..., ge=1, le=50000)
    stock: Optional[int] = Field(None, ge=0)
    image_url: Optional[str] = None


class PointProductUpdate(BaseModel):
    """Schema for updating a point product"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    points_price: Optional[int] = Field(None, ge=1, le=50000)
    stock: Optional[int] = Field(None, ge=0)
    image_url: Optional[str] = None
    is_active: Optional[bool] = None


class PointProductResponse(BaseModel):
    """Schema for point product response"""
    id: int
    family_id: int
    name: str
    description: Optional[str] = None
    points_price: int
    stock: Optional[int] = None
    image_url: Optional[str] = None
    created_by: int
    created_by_user: Optional[UserBriefResponse] = None  # 上架者用户对象
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ============== Purchase Schemas ==============

class PurchaseResponse(BaseModel):
    """Schema for purchase response"""
    id: int
    product_id: int
    product: Optional[PointProductResponse] = None  # 关联的商品对象
    user_id: int
    points_spent: int
    status: str
    use_count: int
    purchased_at: datetime
    used_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ============== Point Transaction Schemas ==============

class PointTransactionResponse(BaseModel):
    """Schema for point transaction response"""
    id: int
    user_id: int
    amount: int
    type: str
    reference_id: Optional[int] = None
    balance_after: int
    description: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
