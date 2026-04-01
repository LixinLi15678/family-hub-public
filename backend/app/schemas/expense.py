"""
Expense and Income schemas
"""
from datetime import datetime, date
from typing import Optional, List
from pydantic import BaseModel, Field


# Expense Category Schemas
class ExpenseCategoryCreate(BaseModel):
    """Schema for creating expense category"""
    name: str = Field(..., min_length=1, max_length=50)
    type: str = Field(..., pattern="^(fixed|supplementary|optional)$")
    parent_id: Optional[int] = None
    icon: Optional[str] = None
    sort_order: int = 0
    is_big_expense: bool = False


class ExpenseCategoryResponse(BaseModel):
    """Schema for expense category response"""
    id: int
    family_id: int
    name: str
    type: str
    parent_id: Optional[int] = None
    icon: Optional[str] = None
    sort_order: int
    is_big_expense: bool = False
    children: Optional[List["ExpenseCategoryResponse"]] = None

    class Config:
        from_attributes = True


# Expense Split Schemas
class ExpenseSplitCreate(BaseModel):
    """Schema for creating expense split"""
    user_id: int
    share_amount: float = Field(..., gt=0)
    share_percentage: Optional[float] = Field(None, ge=0, le=100)


class ExpenseSplitResponse(BaseModel):
    """Schema for expense split response"""
    id: int
    expense_id: int
    user_id: int
    share_amount: float
    share_percentage: Optional[float] = None
    is_paid: bool
    paid_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# Expense Schemas
class ExpenseCreate(BaseModel):
    """Schema for creating expense"""
    category_id: int
    amount: float = Field(..., gt=0)
    currency_id: int
    user_id: Optional[int] = None  # 付款人，如不传则使用当前用户
    description: Optional[str] = Field(None, max_length=255)
    expense_date: date
    is_big_expense: Optional[bool] = None  # 显式标记，如不传则沿用分类标记
    split_only: bool = False  # 仅用于分摊结算，不计入统计；列表展示原始记录用于历史追踪
    splits: Optional[List[ExpenseSplitCreate]] = None


class ExpenseUpdate(BaseModel):
    """Schema for updating expense"""
    category_id: Optional[int] = None
    amount: Optional[float] = Field(None, gt=0)
    currency_id: Optional[int] = None
    description: Optional[str] = Field(None, max_length=255)
    expense_date: Optional[date] = None
    is_settled: Optional[bool] = None
    is_big_expense: Optional[bool] = None
    split_only: Optional[bool] = None
    user_id: Optional[int] = None
    version: int  # Required for optimistic locking


class ExpenseResponse(BaseModel):
    """Schema for expense response"""
    id: int
    family_id: int
    category_id: int
    user_id: int
    allocation_source_id: Optional[int] = None
    allocation_payer_id: Optional[int] = None
    amount: float
    currency_id: int
    description: Optional[str] = None
    expense_date: date
    is_settled: bool
    is_big_expense: bool
    split_only: bool = False
    big_expense_balance: Optional[float] = None
    big_expense_overdrawn: Optional[bool] = None
    big_expense_balance_before: Optional[float] = None
    version: int
    created_at: datetime
    updated_at: datetime
    splits: Optional[List[ExpenseSplitResponse]] = None

    class Config:
        from_attributes = True


# Income Schemas
class IncomeCreate(BaseModel):
    """Schema for creating income"""
    amount: float = Field(..., gt=0)
    currency_id: int
    source: Optional[str] = Field(None, max_length=100)
    income_date: date
    description: Optional[str] = Field(None, max_length=255)
    reserve_mode: Optional[str] = Field(None, pattern="^(percent|fixed|none)?$")
    reserve_value: Optional[float] = Field(None, ge=0)


class IncomeUpdate(BaseModel):
    """Schema for updating income"""
    amount: Optional[float] = Field(None, gt=0)
    currency_id: Optional[int] = None
    source: Optional[str] = Field(None, max_length=100)
    income_date: Optional[date] = None
    description: Optional[str] = Field(None, max_length=255)
    reserve_mode: Optional[str] = Field(None, pattern="^(percent|fixed|none)?$")
    reserve_value: Optional[float] = Field(None, ge=0)


class IncomeResponse(BaseModel):
    """Schema for income response"""
    id: int
    family_id: int
    user_id: int
    amount: float
    currency_id: int
    currency_code: Optional[str] = None
    source: Optional[str] = None
    income_date: date
    description: Optional[str] = None
    reserve_mode: Optional[str] = None
    reserve_value: Optional[float] = None
    big_expense_reserved: float
    created_at: datetime

    class Config:
        from_attributes = True


# Statistics Schemas
class MonthlyStats(BaseModel):
    """Monthly statistics"""
    year: int
    month: int
    total_expense: float
    total_income: float
    balance: float
    essential_expense: float = 0
    supplementary_expense: float = 0
    optional_expense: float = 0
    expense_by_category: dict
    big_expense_reserved: float
    big_expense_expense: float
    big_expense_balance: float
    big_expense_balance_total: Optional[float] = None
    big_expense_balance_month: Optional[float] = None


class SplitSettlement(BaseModel):
    """Net settlement between two users for shared expenses"""
    from_user_id: int
    to_user_id: int
    amount: float


class CategoryStats(BaseModel):
    """Category statistics"""
    category_id: Optional[int] = None  # None 表示未分类
    category_name: str
    total_amount: float
    percentage: float
    count: int


class BigExpenseHistoryItem(BaseModel):
    """History item for big expense budget"""
    year: int
    month: int
    reserved: float
    spent: float
    balance_month: float


class BigExpenseBudgetSummary(BaseModel):
    """Summary of big expense budget and history"""
    balance_total: float
    overdrawn: bool
    history: List[BigExpenseHistoryItem]
