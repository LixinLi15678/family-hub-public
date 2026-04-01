"""
Point shop products routes
"""
from datetime import datetime
import imghdr
from pathlib import Path
from typing import List, Optional
from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models.user import User
from app.models.chore import PointProduct, Purchase, PointTransaction
from app.schemas.chore import (
    PointProductCreate, PointProductUpdate, PointProductResponse,
    PurchaseResponse, UserBriefResponse
)
from app.schemas.common import SuccessResponse
from app.utils.security import get_current_user
from app.utils.error_codes import (
    ErrorCode, APIError,
    raise_not_in_family, raise_not_found,
    raise_insufficient_points, raise_out_of_stock
)

router = APIRouter(prefix="/products", tags=["Products"])


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


@router.get("", response_model=SuccessResponse[List[PointProductResponse]])
async def get_products(
    is_active: Optional[bool] = True,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all products in the point shop"""
    if not current_user.family_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You are not in a family")
    
    query = (
        select(PointProduct)
        .options(selectinload(PointProduct.created_by_user))
        .where(PointProduct.family_id == current_user.family_id)
    )
    
    if is_active is not None:
        query = query.where(PointProduct.is_active == is_active)
    
    query = query.order_by(PointProduct.created_at.desc())
    
    result = await db.execute(query)
    products = result.scalars().all()
    
    return SuccessResponse(
        data=[build_product_response(p) for p in products],
        message="获取成功"
    )


@router.post("/upload-image", response_model=SuccessResponse[dict])
async def upload_product_image(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    """Upload and store a product image, returns a public URL under /uploads."""
    if not current_user.family_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You are not in a family")

    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="只支持上传图片文件")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="空文件")

    if len(content) > settings.UPLOAD_MAX_BYTES:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="图片过大")

    kind = imghdr.what(None, h=content)
    if not kind and file.content_type:
        kind = file.content_type.split("/")[-1].lower()
        if kind == "jpg":
            kind = "jpeg"

    allowed = {"jpeg": "jpg", "png": "png", "gif": "gif", "webp": "webp"}
    ext = allowed.get(kind or "")
    if not ext:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="无法识别的图片格式")

    rel_dir = Path("point-products") / f"family-{current_user.family_id}"
    abs_dir = Path(settings.UPLOAD_DIR) / rel_dir
    abs_dir.mkdir(parents=True, exist_ok=True)

    filename = f"{uuid4().hex}.{ext}"
    abs_path = abs_dir / filename
    abs_path.write_bytes(content)

    url = f"{settings.UPLOAD_PUBLIC_BASE_URL}/{rel_dir.as_posix()}/{filename}"

    return SuccessResponse(data={"url": url}, message="上传成功")


@router.post("", response_model=SuccessResponse[PointProductResponse])
async def create_product(
    product_data: PointProductCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new product in the point shop"""
    if not current_user.family_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You are not in a family")
    
    product = PointProduct(
        family_id=current_user.family_id,
        name=product_data.name,
        description=product_data.description,
        points_price=product_data.points_price,
        stock=product_data.stock,
        image_url=product_data.image_url,
        created_by=current_user.id
    )
    db.add(product)
    await db.flush()
    
    # Reload with relationships
    result = await db.execute(
        select(PointProduct)
        .options(selectinload(PointProduct.created_by_user))
        .where(PointProduct.id == product.id)
    )
    product = result.scalar_one()
    
    return SuccessResponse(
        data=build_product_response(product),
        message="商品上架成功"
    )


@router.put("/{product_id}", response_model=SuccessResponse[PointProductResponse])
async def update_product(
    product_id: int,
    product_data: PointProductUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a product"""
    if not current_user.family_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You are not in a family")
    
    result = await db.execute(
        select(PointProduct)
        .options(selectinload(PointProduct.created_by_user))
        .where(
            PointProduct.id == product_id,
            PointProduct.family_id == current_user.family_id
        )
    )
    product = result.scalar_one_or_none()
    
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    
    # Update fields
    update_data = product_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(product, key, value)
    
    await db.flush()
    
    # Reload with relationships
    result = await db.execute(
        select(PointProduct)
        .options(selectinload(PointProduct.created_by_user))
        .where(PointProduct.id == product.id)
    )
    product = result.scalar_one()
    
    return SuccessResponse(
        data=build_product_response(product),
        message="商品已更新"
    )


@router.delete("/{product_id}", response_model=SuccessResponse[dict])
async def delete_product(
    product_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Remove a product from the shop (soft delete)"""
    if not current_user.family_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You are not in a family")
    
    result = await db.execute(
        select(PointProduct).where(
            PointProduct.id == product_id,
            PointProduct.family_id == current_user.family_id
        )
    )
    product = result.scalar_one_or_none()
    
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    
    # Soft delete
    product.is_active = False
    
    return SuccessResponse(data={}, message="商品已下架")


@router.post("/{product_id}/purchase", response_model=SuccessResponse[PurchaseResponse])
async def purchase_product(
    product_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Purchase a product with points.
    
    Transaction flow:
    1. Validate user is in a family
    2. Validate product exists and is active
    3. Check user has sufficient points
    4. Check product has stock (if limited)
    5. Atomically: deduct points, create purchase record, update stock
    """
    # Step 1: Check user is in a family
    if not current_user.family_id:
        raise_not_in_family()
    
    # Step 2: Get and validate product (使用 FOR UPDATE 锁定行，防止并发问题)
    result = await db.execute(
        select(PointProduct)
        .options(selectinload(PointProduct.created_by_user))
        .where(
            PointProduct.id == product_id,
            PointProduct.family_id == current_user.family_id
        )
        .with_for_update()  # 加行锁防止并发购买
    )
    product = result.scalar_one_or_none()
    
    if not product:
        raise_not_found("商品", ErrorCode.PRODUCT_NOT_FOUND)
    
    if not product.is_active:
        raise APIError(
            error_code=ErrorCode.PRODUCT_NOT_AVAILABLE,
            message="商品已下架，无法购买",
            status_code=status.HTTP_400_BAD_REQUEST
        )
    
    # Step 3: Check user has enough points
    if current_user.points_balance < product.points_price:
        raise_insufficient_points(
            required=product.points_price,
            current=current_user.points_balance
        )
    
    # Step 4: Check stock availability
    if product.stock is not None and product.stock <= 0:
        raise_out_of_stock()
    
    # Step 5: Execute purchase transaction (all or nothing)
    try:
        # 如果有限库存，使用原子更新确保库存扣减正确
        if product.stock is not None:
            # 使用条件更新，确保库存充足
            result = await db.execute(
                update(PointProduct)
                .where(
                    PointProduct.id == product_id,
                    PointProduct.stock > 0  # 确保库存大于0
                )
                .values(stock=PointProduct.stock - 1)
            )
            if result.rowcount == 0:
                # 库存不足
                raise_out_of_stock()
        
        # Deduct points from user
        current_user.points_balance -= product.points_price
        
        # Create purchase record
        purchase = Purchase(
            product_id=product.id,
            user_id=current_user.id,
            points_spent=product.points_price
        )
        db.add(purchase)
        await db.flush()  # Get purchase ID
        
        # Create point transaction record
        transaction = PointTransaction(
            user_id=current_user.id,
            amount=-product.points_price,
            type="purchase",
            reference_id=purchase.id,
            balance_after=current_user.points_balance,
            description=f"购买商品: {product.name}"
        )
        db.add(transaction)
        
        await db.flush()
        
        # Reload purchase with relationships
        result = await db.execute(
            select(Purchase)
            .options(
                selectinload(Purchase.product).selectinload(PointProduct.created_by_user)
            )
            .where(Purchase.id == purchase.id)
        )
        purchase = result.scalar_one()
        
    except Exception as e:
        # Rollback will be handled by the session context manager
        raise APIError(
            error_code=ErrorCode.INVALID_OPERATION,
            message="购买失败，请稍后重试",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details={"error": str(e)}
        )
    
    return SuccessResponse(
        data=build_purchase_response(purchase),
        message=f"购买成功！消费 {product.points_price} 钻石"
    )
