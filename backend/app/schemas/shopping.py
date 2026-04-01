"""
Shopping list schemas
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


# Store Schemas
class StoreCreate(BaseModel):
    """Schema for creating a store"""
    name: str = Field(..., min_length=1, max_length=100)
    icon: Optional[str] = None
    sort_order: int = 0


class StoreResponse(BaseModel):
    """Schema for store response"""
    id: int
    family_id: int
    name: str
    icon: Optional[str] = None
    sort_order: int

    class Config:
        from_attributes = True


# Shopping List Schemas
class ShoppingListCreate(BaseModel):
    """Schema for creating a shopping list"""
    name: str = Field(..., min_length=1, max_length=100)


class ShoppingListResponse(BaseModel):
    """Schema for shopping list response"""
    id: int
    family_id: int
    name: str
    is_active: bool
    created_by: int
    created_at: datetime
    items_count: Optional[int] = None
    checked_count: Optional[int] = None

    class Config:
        from_attributes = True


# Shopping Item Schemas
class ShoppingItemCreate(BaseModel):
    """Schema for creating a shopping item"""
    list_id: int
    store_id: Optional[int] = None
    name: str = Field(..., min_length=1, max_length=100)
    quantity: int = Field(default=1, ge=1)
    unit: Optional[str] = Field(None, max_length=20)
    note: Optional[str] = Field(None, max_length=255)


class ShoppingItemUpdate(BaseModel):
    """Schema for updating a shopping item"""
    store_id: Optional[int] = None
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    quantity: Optional[int] = Field(None, ge=1)
    unit: Optional[str] = Field(None, max_length=20)
    note: Optional[str] = Field(None, max_length=255)
    version: int  # Required for optimistic locking


class ShoppingItemResponse(BaseModel):
    """Schema for shopping item response"""
    id: int
    list_id: int
    store_id: Optional[int] = None
    name: str
    quantity: int
    unit: Optional[str] = None
    note: Optional[str] = None
    is_checked: bool
    checked_by: Optional[int] = None
    checked_at: Optional[datetime] = None
    added_by: int
    version: int
    created_at: datetime

    class Config:
        from_attributes = True

