"""
User routes
"""
from datetime import datetime
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select, func, case
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.models.chore import Purchase, PointTransaction, PointProduct
from app.schemas.user import UserResponse, UserUpdate, DailyLoginRewardRequest, DailyLoginRewardResponse
from app.schemas.chore import PurchaseResponse, PointTransactionResponse, PointProductResponse, UserBriefResponse
from app.schemas.common import SuccessResponse, PaginatedResponse, PaginatedData
from app.utils.security import get_current_user
from app.validators import normalize_local_date
from app.services.points_service import PointsService

router = APIRouter(prefix="/users", tags=["Users"])


def build_product_response(product: PointProduct) -> PointProductResponse:
    """Build PointProductResponse with related user objects"""
    response = PointProductResponse.model_validate(product)
    
    # Add created_by_user if available
    if product.created_by_user:
        response.created_by_user = UserBriefResponse.model_validate(product.created_by_user)
    
    return response


def build_purchase_response(purchase: Purchase) -> PurchaseResponse:
    """Build PurchaseResponse with related product object"""
    response = PurchaseResponse.model_validate(purchase)
    
    # Add product if available
    if purchase.product:
        response.product = build_product_response(purchase.product)
    
    return response


@router.get("/me", response_model=SuccessResponse[UserResponse])
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """Get current user information"""
    return SuccessResponse(
        data=UserResponse.model_validate(current_user),
        message="获取成功"
    )


@router.patch("/me", response_model=SuccessResponse[UserResponse])
async def update_current_user(
    user_data: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update current user profile"""
    # Check if username is taken by another user
    if user_data.username:
        result = await db.execute(
            select(User).where(
                User.username == user_data.username,
                User.id != current_user.id
            )
        )
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already taken"
            )
    
    # Update fields
    update_data = user_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(current_user, key, value)
    
    await db.flush()
    await db.refresh(current_user)
    
    return SuccessResponse(
        data=UserResponse.model_validate(current_user),
        message="个人信息已更新"
    )


@router.get("/me/points", response_model=SuccessResponse[dict])
async def get_points_balance(
    current_user: User = Depends(get_current_user)
):
    """Get current user's points balance"""
    return SuccessResponse(
        data={
            "user_id": current_user.id,
            "username": current_user.username,
            "points_balance": current_user.points_balance
        },
        message="获取成功"
    )


@router.get("/me/transactions", response_model=PaginatedResponse[PointTransactionResponse])
async def get_point_transactions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get current user's point transactions"""
    query = select(PointTransaction).where(PointTransaction.user_id == current_user.id)
    
    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar()
    
    # Get paginated results
    query = query.order_by(PointTransaction.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    
    result = await db.execute(query)
    transactions = result.scalars().all()

    summary_result = await db.execute(
        select(
            func.coalesce(
                func.sum(case((PointTransaction.amount > 0, PointTransaction.amount), else_=0)),
                0,
            ).label("total_earned"),
            func.coalesce(
                func.sum(case((PointTransaction.amount < 0, -PointTransaction.amount), else_=0)),
                0,
            ).label("total_spent"),
        ).where(PointTransaction.user_id == current_user.id)
    )
    total_earned, total_spent = summary_result.one()
    
    return PaginatedResponse(
        data=PaginatedData(
            items=[PointTransactionResponse.model_validate(t) for t in transactions],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=(total + page_size - 1) // page_size,
            summary={
                "total_earned": int(total_earned or 0),
                "total_spent": int(total_spent or 0),
                "net": int((total_earned or 0) - (total_spent or 0)),
                "balance": int(current_user.points_balance),
            },
        )
    )


@router.get("/me/purchases", response_model=SuccessResponse[List[PurchaseResponse]])
async def get_purchases(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get current user's purchases with product details"""
    result = await db.execute(
        select(Purchase)
        .options(
            selectinload(Purchase.product).selectinload(PointProduct.created_by_user)
        )
        .where(Purchase.user_id == current_user.id)
        .order_by(Purchase.purchased_at.desc())
    )
    purchases = result.scalars().all()
    
    return SuccessResponse(
        data=[build_purchase_response(p) for p in purchases],
        message="获取成功"
    )


@router.patch("/purchases/{purchase_id}/use", response_model=SuccessResponse[PurchaseResponse])
async def use_purchase(
    purchase_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Mark a purchased item as used"""
    result = await db.execute(
        select(Purchase)
        .options(
            selectinload(Purchase.product).selectinload(PointProduct.created_by_user)
        )
        .where(
            Purchase.id == purchase_id,
            Purchase.user_id == current_user.id
        )
    )
    purchase = result.scalar_one_or_none()
    
    if not purchase:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Purchase not found")
    
    # Update use count and status
    purchase.use_count += 1
    purchase.used_at = datetime.utcnow()
    if purchase.status == "owned":
        purchase.status = "used"
    
    await db.flush()
    
    # Reload with relationships
    result = await db.execute(
        select(Purchase)
        .options(
            selectinload(Purchase.product).selectinload(PointProduct.created_by_user)
        )
        .where(Purchase.id == purchase.id)
    )
    purchase = result.scalar_one()
    
    return SuccessResponse(
        data=build_purchase_response(purchase),
        message="商品已使用"
    )


@router.post("/me/daily-login-reward", response_model=SuccessResponse[DailyLoginRewardResponse])
async def claim_daily_login_reward(
    payload: DailyLoginRewardRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Claim daily first-login reward (10 diamonds).

    The reward is granted once per `local_date` provided by the client (local timezone).
    """
    try:
        local_date = normalize_local_date(payload.local_date)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    if current_user.last_daily_login_reward_date == local_date:
        return SuccessResponse(
            data=DailyLoginRewardResponse(
                awarded=False,
                amount=0,
                local_date=local_date,
                points_balance=current_user.points_balance,
            ),
            message="今日已领取",
        )

    points_service = PointsService(db)
    await points_service.add_points(
        user=current_user,
        amount=10,
        transaction_type="bonus",
        description="每日首次登录奖励",
    )
    current_user.last_daily_login_reward_date = local_date

    await db.flush()
    await db.refresh(current_user)

    return SuccessResponse(
        data=DailyLoginRewardResponse(
            awarded=True,
            amount=10,
            local_date=local_date,
            points_balance=current_user.points_balance,
        ),
        message="领取成功",
    )
