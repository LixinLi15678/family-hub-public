"""
Family management routes
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.models.family import Family
from app.schemas.family import FamilyCreate, FamilyResponse, FamilyJoin, FamilyMemberResponse
from app.schemas.common import SuccessResponse
from app.utils.security import get_current_user, generate_invite_code
from app.utils.seed_data import seed_family_defaults, get_chore_templates, get_category_suggestions, get_store_suggestions

router = APIRouter(prefix="/families", tags=["Families"])


@router.post("", response_model=SuccessResponse[FamilyResponse])
async def create_family(
    family_data: FamilyCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new family"""
    if current_user.family_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You are already in a family"
        )
    
    # Generate unique invite code
    invite_code = generate_invite_code()
    while True:
        result = await db.execute(select(Family).where(Family.invite_code == invite_code))
        if not result.scalar_one_or_none():
            break
        invite_code = generate_invite_code()
    
    # Create family
    family = Family(
        name=family_data.name,
        invite_code=invite_code
    )
    db.add(family)
    await db.flush()
    
    # Add current user to family as admin
    current_user.family_id = family.id
    current_user.role = "admin"
    await db.flush()
    await db.refresh(family)
    await db.refresh(current_user)
    
    # Seed default data for the new family (categories, stores)
    await seed_family_defaults(db, family.id)
    
    # Build response without lazy loading members
    response = FamilyResponse(
        id=family.id,
        name=family.name,
        invite_code=family.invite_code,
        created_at=family.created_at,
        members=[FamilyMemberResponse.model_validate(current_user)]
    )
    
    return SuccessResponse(
        data=response,
        message="家庭创建成功"
    )


@router.get("/me", response_model=SuccessResponse[FamilyResponse])
async def get_my_family(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get current user's family"""
    if not current_user.family_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="You are not in any family"
        )
    
    result = await db.execute(
        select(Family)
        .options(selectinload(Family.members))
        .where(Family.id == current_user.family_id)
    )
    family = result.scalar_one_or_none()
    
    if not family:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Family not found"
        )
    
    response = FamilyResponse.model_validate(family)
    response.members = [FamilyMemberResponse.model_validate(m) for m in family.members]
    
    return SuccessResponse(data=response, message="获取成功")


@router.post("/join", response_model=SuccessResponse[FamilyResponse])
async def join_family(
    join_data: FamilyJoin,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Join a family using invite code"""
    if current_user.family_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You are already in a family"
        )
    
    result = await db.execute(
        select(Family)
        .options(selectinload(Family.members))
        .where(Family.invite_code == join_data.invite_code)
    )
    family = result.scalar_one_or_none()
    
    if not family:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid invite code"
        )
    
    # Add user to family
    current_user.family_id = family.id
    current_user.role = "member"
    await db.flush()
    await db.refresh(family)
    
    response = FamilyResponse.model_validate(family)
    response.members = [FamilyMemberResponse.model_validate(m) for m in family.members]
    
    return SuccessResponse(
        data=response,
        message="成功加入家庭"
    )


@router.get("/members", response_model=SuccessResponse[List[FamilyMemberResponse]])
async def get_family_members(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all family members"""
    if not current_user.family_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="You are not in any family"
        )
    
    result = await db.execute(
        select(User).where(User.family_id == current_user.family_id)
    )
    members = result.scalars().all()
    
    return SuccessResponse(
        data=[FamilyMemberResponse.model_validate(m) for m in members],
        message="获取成功"
    )


@router.put("/invite-code", response_model=SuccessResponse[FamilyResponse])
async def regenerate_invite_code(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Regenerate family invite code (admin only)"""
    if not current_user.family_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="You are not in any family"
        )
    
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin can regenerate invite code"
        )
    
    result = await db.execute(
        select(Family).where(Family.id == current_user.family_id)
    )
    family = result.scalar_one_or_none()
    
    if not family:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Family not found"
        )
    
    # Generate new invite code
    new_code = generate_invite_code()
    while True:
        result = await db.execute(select(Family).where(Family.invite_code == new_code))
        if not result.scalar_one_or_none():
            break
        new_code = generate_invite_code()
    
    family.invite_code = new_code
    await db.flush()
    await db.refresh(family)
    
    return SuccessResponse(
        data=FamilyResponse.model_validate(family),
        message="邀请码已更新"
    )


# ============== Suggestions Endpoints ==============

@router.get("/suggestions/categories", response_model=SuccessResponse[list])
async def get_category_suggestions_endpoint(
    current_user: User = Depends(get_current_user)
):
    """Get default expense category suggestions"""
    return SuccessResponse(
        data=get_category_suggestions(),
        message="获取成功"
    )


@router.get("/suggestions/stores", response_model=SuccessResponse[list])
async def get_store_suggestions_endpoint(
    current_user: User = Depends(get_current_user)
):
    """Get default store suggestions"""
    return SuccessResponse(
        data=get_store_suggestions(),
        message="获取成功"
    )


@router.get("/suggestions/chores", response_model=SuccessResponse[list])
async def get_chore_templates_endpoint(
    current_user: User = Depends(get_current_user)
):
    """Get chore task templates as suggestions"""
    return SuccessResponse(
        data=get_chore_templates(),
        message="获取成功"
    )

