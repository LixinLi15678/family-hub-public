"""
Shopping list routes
"""
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.models.shopping import Store, ShoppingList, ShoppingItem
from app.schemas.shopping import (
    StoreCreate, StoreResponse,
    ShoppingListCreate, ShoppingListResponse,
    ShoppingItemCreate, ShoppingItemUpdate, ShoppingItemResponse
)
from app.schemas.common import SuccessResponse
from app.utils.security import get_current_user

router = APIRouter(prefix="/shopping", tags=["Shopping"])


# ============== Stores ==============

@router.get("/stores", response_model=SuccessResponse[List[StoreResponse]])
async def get_stores(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all stores for the family"""
    if not current_user.family_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You are not in a family")
    
    result = await db.execute(
        select(Store)
        .where(Store.family_id == current_user.family_id)
        .order_by(Store.sort_order)
    )
    stores = result.scalars().all()
    
    return SuccessResponse(
        data=[StoreResponse.model_validate(s) for s in stores],
        message="获取成功"
    )


@router.post("/stores", response_model=SuccessResponse[StoreResponse])
async def create_store(
    store_data: StoreCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new store"""
    if not current_user.family_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You are not in a family")
    
    store = Store(
        family_id=current_user.family_id,
        name=store_data.name,
        icon=store_data.icon,
        sort_order=store_data.sort_order
    )
    db.add(store)
    await db.flush()
    await db.refresh(store)
    
    return SuccessResponse(
        data=StoreResponse.model_validate(store),
        message="商店创建成功"
    )


# ============== Shopping Lists ==============

@router.get("/lists", response_model=SuccessResponse[List[ShoppingListResponse]])
async def get_shopping_lists(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all shopping lists"""
    if not current_user.family_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You are not in a family")
    
    result = await db.execute(
        select(ShoppingList)
        .options(selectinload(ShoppingList.items))
        .where(ShoppingList.family_id == current_user.family_id)
        .order_by(ShoppingList.created_at.desc())
    )
    lists = result.scalars().all()
    
    response_data = []
    for lst in lists:
        data = ShoppingListResponse.model_validate(lst)
        data.items_count = len(lst.items)
        data.checked_count = sum(1 for item in lst.items if item.is_checked)
        response_data.append(data)
    
    return SuccessResponse(data=response_data, message="获取成功")


@router.post("/lists", response_model=SuccessResponse[ShoppingListResponse])
async def create_shopping_list(
    list_data: ShoppingListCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new shopping list"""
    if not current_user.family_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You are not in a family")
    
    shopping_list = ShoppingList(
        family_id=current_user.family_id,
        name=list_data.name,
        created_by=current_user.id
    )
    db.add(shopping_list)
    await db.flush()
    await db.refresh(shopping_list)
    
    response = ShoppingListResponse.model_validate(shopping_list)
    response.items_count = 0
    response.checked_count = 0
    
    return SuccessResponse(data=response, message="购物清单创建成功")


@router.get("/lists/{list_id}", response_model=SuccessResponse[ShoppingListResponse])
async def get_shopping_list(
    list_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific shopping list"""
    if not current_user.family_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You are not in a family")
    
    result = await db.execute(
        select(ShoppingList)
        .options(selectinload(ShoppingList.items))
        .where(
            ShoppingList.id == list_id,
            ShoppingList.family_id == current_user.family_id
        )
    )
    shopping_list = result.scalar_one_or_none()
    
    if not shopping_list:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shopping list not found")
    
    response = ShoppingListResponse.model_validate(shopping_list)
    response.items_count = len(shopping_list.items)
    response.checked_count = sum(1 for item in shopping_list.items if item.is_checked)
    
    return SuccessResponse(data=response, message="获取成功")


@router.delete("/lists/{list_id}", response_model=SuccessResponse[dict])
async def delete_shopping_list(
    list_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a shopping list"""
    if not current_user.family_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You are not in a family")
    
    result = await db.execute(
        select(ShoppingList).where(
            ShoppingList.id == list_id,
            ShoppingList.family_id == current_user.family_id
        )
    )
    shopping_list = result.scalar_one_or_none()
    
    if not shopping_list:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shopping list not found")
    
    await db.delete(shopping_list)
    
    return SuccessResponse(data={}, message="购物清单已删除")


# ============== Shopping Items ==============

@router.get("/lists/{list_id}/items", response_model=SuccessResponse[List[ShoppingItemResponse]])
async def get_shopping_items(
    list_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all items in a shopping list"""
    if not current_user.family_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You are not in a family")
    
    # Verify list belongs to family
    result = await db.execute(
        select(ShoppingList).where(
            ShoppingList.id == list_id,
            ShoppingList.family_id == current_user.family_id
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shopping list not found")
    
    result = await db.execute(
        select(ShoppingItem)
        .where(ShoppingItem.list_id == list_id)
        .order_by(ShoppingItem.is_checked, ShoppingItem.created_at)
    )
    items = result.scalars().all()
    
    return SuccessResponse(
        data=[ShoppingItemResponse.model_validate(item) for item in items],
        message="获取成功"
    )


@router.post("/items", response_model=SuccessResponse[ShoppingItemResponse])
async def create_shopping_item(
    item_data: ShoppingItemCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Add an item to a shopping list"""
    if not current_user.family_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You are not in a family")
    
    # Verify list belongs to family
    result = await db.execute(
        select(ShoppingList).where(
            ShoppingList.id == item_data.list_id,
            ShoppingList.family_id == current_user.family_id
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shopping list not found")
    
    item = ShoppingItem(
        list_id=item_data.list_id,
        store_id=item_data.store_id,
        name=item_data.name,
        quantity=item_data.quantity,
        unit=item_data.unit,
        note=item_data.note,
        added_by=current_user.id
    )
    db.add(item)
    await db.flush()
    await db.refresh(item)
    
    return SuccessResponse(
        data=ShoppingItemResponse.model_validate(item),
        message="商品已添加"
    )


@router.patch("/items/{item_id}", response_model=SuccessResponse[ShoppingItemResponse])
async def update_shopping_item(
    item_id: int,
    item_data: ShoppingItemUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a shopping item"""
    if not current_user.family_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You are not in a family")
    
    result = await db.execute(
        select(ShoppingItem)
        .join(ShoppingList)
        .where(
            ShoppingItem.id == item_id,
            ShoppingList.family_id == current_user.family_id
        )
    )
    item = result.scalar_one_or_none()
    
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    
    # Optimistic locking check
    if item.version != item_data.version:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="数据已被修改，请刷新后重试"
        )
    
    # Update fields
    update_data = item_data.model_dump(exclude_unset=True, exclude={"version"})
    for key, value in update_data.items():
        setattr(item, key, value)
    item.version += 1
    
    await db.flush()
    await db.refresh(item)
    
    return SuccessResponse(
        data=ShoppingItemResponse.model_validate(item),
        message="商品已更新"
    )


@router.patch("/items/{item_id}/check", response_model=SuccessResponse[ShoppingItemResponse])
async def toggle_item_check(
    item_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Toggle item checked status"""
    if not current_user.family_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You are not in a family")
    
    result = await db.execute(
        select(ShoppingItem)
        .join(ShoppingList)
        .where(
            ShoppingItem.id == item_id,
            ShoppingList.family_id == current_user.family_id
        )
    )
    item = result.scalar_one_or_none()
    
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    
    # Toggle check status
    item.is_checked = not item.is_checked
    item.checked_by = current_user.id if item.is_checked else None
    item.checked_at = datetime.utcnow() if item.is_checked else None
    item.version += 1
    
    await db.flush()
    await db.refresh(item)
    
    return SuccessResponse(
        data=ShoppingItemResponse.model_validate(item),
        message="已勾选" if item.is_checked else "已取消勾选"
    )


@router.delete("/items/{item_id}", response_model=SuccessResponse[dict])
async def delete_shopping_item(
    item_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a shopping item"""
    if not current_user.family_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You are not in a family")
    
    result = await db.execute(
        select(ShoppingItem)
        .join(ShoppingList)
        .where(
            ShoppingItem.id == item_id,
            ShoppingList.family_id == current_user.family_id
        )
    )
    item = result.scalar_one_or_none()
    
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    
    await db.delete(item)
    
    return SuccessResponse(data={}, message="商品已删除")

