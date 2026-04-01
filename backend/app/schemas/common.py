"""
Common response schemas
"""
from typing import Any, Generic, List, Optional, TypeVar
from pydantic import BaseModel

T = TypeVar("T")


class SuccessResponse(BaseModel, Generic[T]):
    """Standard success response"""
    success: bool = True
    data: T
    message: str = "操作成功"


class PaginatedData(BaseModel, Generic[T]):
    """Paginated data container"""
    items: List[T]
    total: int
    page: int
    page_size: int
    total_pages: int
    summary: Optional[dict[str, Any]] = None


class PaginatedResponse(BaseModel, Generic[T]):
    """Paginated response"""
    success: bool = True
    data: PaginatedData[T]


class ErrorDetail(BaseModel):
    """Error detail"""
    code: str
    message: str
    details: Optional[dict] = None


class ErrorResponse(BaseModel):
    """Standard error response"""
    success: bool = False
    error: ErrorDetail
