"""
Trip and Budget schemas
"""
from datetime import datetime, date
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict


# Trip Schemas
class TripCreate(BaseModel):
    """Schema for creating a trip"""
    name: str = Field(..., min_length=1, max_length=100)
    destination: Optional[str] = Field(None, max_length=100)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    total_budget: Optional[float] = Field(None, ge=0)
    currency_id: Optional[int] = None
    # 兼容前端传入的 currency 字段（币种代码）
    currency_code: Optional[str] = Field(None, alias="currency")

    model_config = ConfigDict(populate_by_name=True)


class TripUpdate(BaseModel):
    """Schema for updating a trip"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    destination: Optional[str] = Field(None, max_length=100)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    total_budget: Optional[float] = Field(None, ge=0)
    currency_id: Optional[int] = None
    # 兼容前端传入的 currency 字段（币种代码）
    currency_code: Optional[str] = Field(None, alias="currency")
    status: Optional[str] = Field(None, pattern="^(planned|active|completed)$")

    model_config = ConfigDict(populate_by_name=True)


class TripResponse(BaseModel):
    """Schema for trip response"""
    id: int
    family_id: int
    name: str
    destination: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    total_budget: Optional[float] = None
    currency_id: Optional[int] = None
    currency_code: Optional[str] = None
    total_spent: Optional[float] = None
    status: str = "planned"  # planned/active/completed
    created_by: int
    created_at: datetime

    class Config:
        from_attributes = True


# Trip Budget Schemas
class TripBudgetCreate(BaseModel):
    """Schema for creating a trip budget"""
    category: str = Field(..., min_length=1, max_length=50)
    budget_amount: float = Field(..., ge=0)


class TripBudgetUpdate(BaseModel):
    """Schema for updating a trip budget"""
    category: Optional[str] = Field(None, min_length=1, max_length=50)
    budget_amount: Optional[float] = Field(None, ge=0)


class TripBudgetResponse(BaseModel):
    """Schema for trip budget response"""
    id: int
    trip_id: int
    category: str
    budget_amount: float
    spent_amount: Optional[float] = None

    class Config:
        from_attributes = True


# Trip Expense Schemas
class TripExpenseCreate(BaseModel):
    """Schema for creating a trip expense"""
    budget_id: Optional[int] = None
    amount: float = Field(..., gt=0)
    currency_id: Optional[int] = None  # 可选，默认使用旅行的币种
    currency_code: Optional[str] = Field(None, alias="currency")
    description: Optional[str] = Field(None, max_length=255)
    expense_date: Optional[date] = None

    model_config = ConfigDict(populate_by_name=True)


class TripExpenseUpdate(BaseModel):
    """Schema for updating a trip expense"""
    budget_id: Optional[int] = None
    user_id: Optional[int] = None
    amount: Optional[float] = Field(None, gt=0)
    currency_id: Optional[int] = None
    currency_code: Optional[str] = Field(None, alias="currency")
    description: Optional[str] = Field(None, max_length=255)
    expense_date: Optional[date] = None

    model_config = ConfigDict(populate_by_name=True)


class TripExpenseResponse(BaseModel):
    """Schema for trip expense response"""
    id: int
    trip_id: int
    budget_id: Optional[int] = None
    user_id: int
    amount: float
    currency_id: Optional[int] = None
    currency_code: Optional[str] = None
    split_source_expense_id: Optional[int] = None
    category: Optional[str] = None
    description: Optional[str] = None
    expense_date: Optional[date] = None
    created_at: datetime

    class Config:
        from_attributes = True


class TripExpenseSplitBatch(BaseModel):
    """Batch-split selected trip expenses into a split-only expense (for settlement)."""
    expense_ids: List[int]
    split_user_ids: List[int]


# Trip Statistics
class BudgetVsActual(BaseModel):
    """Budget vs Actual for a category"""
    category: str
    budget: float
    actual: float
    remaining: float
    percentage_used: float


class TripStatsResponse(BaseModel):
    """Trip statistics response"""
    trip_id: int
    total_budget: float
    total_spent: float
    total_remaining: float
    by_category: List[BudgetVsActual]
