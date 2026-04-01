"""
Standardized API error codes
"""
from enum import Enum
from typing import Optional
from fastapi import HTTPException, status


class ErrorCode(str, Enum):
    """Standardized error codes for the API"""
    
    # Authentication errors 1xxx
    INVALID_CREDENTIALS = "AUTH_1001"
    TOKEN_EXPIRED = "AUTH_1002"
    TOKEN_INVALID = "AUTH_1003"
    USER_NOT_FOUND = "AUTH_1004"
    EMAIL_ALREADY_EXISTS = "AUTH_1005"
    USERNAME_ALREADY_EXISTS = "AUTH_1006"
    
    # Family errors 2xxx
    NOT_IN_FAMILY = "FAMILY_2001"
    INVALID_INVITE_CODE = "FAMILY_2002"
    ALREADY_IN_FAMILY = "FAMILY_2003"
    NOT_FAMILY_ADMIN = "FAMILY_2004"
    FAMILY_NOT_FOUND = "FAMILY_2005"
    
    # Business logic errors 3xxx
    INSUFFICIENT_POINTS = "POINTS_3001"
    OUT_OF_STOCK = "SHOP_3002"
    CONFLICT_VERSION = "DATA_3003"
    RESOURCE_NOT_FOUND = "DATA_3004"
    INVALID_OPERATION = "DATA_3005"
    
    # Shopping errors 31xx
    SHOPPING_LIST_NOT_FOUND = "SHOP_3101"
    SHOPPING_ITEM_NOT_FOUND = "SHOP_3102"
    
    # Expense errors 32xx
    EXPENSE_NOT_FOUND = "EXPENSE_3201"
    CATEGORY_NOT_FOUND = "EXPENSE_3202"
    SPLIT_NOT_FOUND = "EXPENSE_3203"
    
    # Chore errors 33xx
    CHORE_NOT_FOUND = "CHORE_3301"
    CHORE_NOT_ACTIVE = "CHORE_3302"
    
    # Product/Shop errors 34xx
    PRODUCT_NOT_FOUND = "PRODUCT_3401"
    PRODUCT_NOT_AVAILABLE = "PRODUCT_3402"
    
    # Trip errors 35xx
    TRIP_NOT_FOUND = "TRIP_3501"
    BUDGET_NOT_FOUND = "TRIP_3502"
    
    # Validation errors 4xxx
    VALIDATION_ERROR = "VALIDATION_4001"
    INVALID_INPUT = "VALIDATION_4002"


class APIError(HTTPException):
    """Custom API exception with error code"""
    
    def __init__(
        self,
        error_code: ErrorCode,
        message: str,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        details: Optional[dict] = None
    ):
        self.error_code = error_code
        self.message = message
        self.details = details
        
        super().__init__(
            status_code=status_code,
            detail={
                "success": False,
                "error": {
                    "code": error_code.value,
                    "message": message,
                    "details": details
                }
            }
        )


# Convenience functions for common errors
def raise_not_in_family():
    """Raise error when user is not in a family"""
    raise APIError(
        error_code=ErrorCode.NOT_IN_FAMILY,
        message="你还没有加入任何家庭",
        status_code=status.HTTP_400_BAD_REQUEST
    )


def raise_not_found(resource: str, error_code: ErrorCode = ErrorCode.RESOURCE_NOT_FOUND):
    """Raise error when resource is not found"""
    raise APIError(
        error_code=error_code,
        message=f"{resource}不存在",
        status_code=status.HTTP_404_NOT_FOUND
    )


def raise_insufficient_points(required: int, current: int):
    """Raise error when user doesn't have enough points"""
    raise APIError(
        error_code=ErrorCode.INSUFFICIENT_POINTS,
        message=f"钻石不足，需要 {required} 钻石，当前余额 {current} 钻石",
        status_code=status.HTTP_400_BAD_REQUEST,
        details={"required": required, "current": current}
    )


def raise_out_of_stock():
    """Raise error when product is out of stock"""
    raise APIError(
        error_code=ErrorCode.OUT_OF_STOCK,
        message="商品已售罄",
        status_code=status.HTTP_400_BAD_REQUEST
    )


def raise_conflict_version():
    """Raise error on optimistic locking conflict"""
    raise APIError(
        error_code=ErrorCode.CONFLICT_VERSION,
        message="数据已被修改，请刷新后重试",
        status_code=status.HTTP_409_CONFLICT
    )


def raise_not_admin():
    """Raise error when user is not family admin"""
    raise APIError(
        error_code=ErrorCode.NOT_FAMILY_ADMIN,
        message="只有管理员可以执行此操作",
        status_code=status.HTTP_403_FORBIDDEN
    )


def raise_invalid_invite_code():
    """Raise error for invalid invite code"""
    raise APIError(
        error_code=ErrorCode.INVALID_INVITE_CODE,
        message="邀请码无效",
        status_code=status.HTTP_404_NOT_FOUND
    )


def raise_already_in_family():
    """Raise error when user already in a family"""
    raise APIError(
        error_code=ErrorCode.ALREADY_IN_FAMILY,
        message="你已经在一个家庭中了",
        status_code=status.HTTP_400_BAD_REQUEST
    )
