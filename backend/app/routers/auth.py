"""
Authentication routes
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.models.family import Family
from app.schemas.user import UserCreate, UserLogin, UserResponse, Token, AuthResponse
from app.schemas.common import SuccessResponse
from app.utils.security import (
    get_password_hash, verify_password,
    create_access_token, create_refresh_token, verify_token,
    generate_invite_code
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=SuccessResponse[AuthResponse])
async def register(user_data: UserCreate, db: AsyncSession = Depends(get_db)):
    """Register a new user"""
    # Check if email already exists
    result = await db.execute(select(User).where(User.email == user_data.email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Check if username already exists
    result = await db.execute(select(User).where(User.username == user_data.username))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken"
        )
    
    # Handle family creation or joining
    family = None
    user_role = "member"
    
    if user_data.family_name:
        # Create new family
        family = Family(
            name=user_data.family_name,
            invite_code=generate_invite_code()
        )
        db.add(family)
        await db.flush()
        user_role = "admin"  # Creator is admin
    elif user_data.invite_code:
        # Join existing family
        result = await db.execute(
            select(Family).where(Family.invite_code == user_data.invite_code)
        )
        family = result.scalar_one_or_none()
        if not family:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid invite code"
            )
    
    # Create new user
    user = User(
        username=user_data.username,
        email=user_data.email,
        password_hash=get_password_hash(user_data.password),
        family_id=family.id if family else None,
        role=user_role
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    
    # Create tokens
    token_data = {"user_id": user.id, "email": user.email}
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)
    
    return SuccessResponse(
        data=AuthResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            user=UserResponse.model_validate(user)
        ),
        message="注册成功"
    )


@router.post("/login", response_model=SuccessResponse[AuthResponse])
async def login(login_data: UserLogin, db: AsyncSession = Depends(get_db)):
    """Login and get JWT tokens"""
    # Find user by email
    result = await db.execute(select(User).where(User.email == login_data.email))
    user = result.scalar_one_or_none()
    
    if not user or not verify_password(login_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    # Create tokens
    token_data = {"user_id": user.id, "email": user.email}
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)
    
    return SuccessResponse(
        data=AuthResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            user=UserResponse.model_validate(user)
        ),
        message="登录成功"
    )


@router.post("/refresh", response_model=SuccessResponse[Token])
async def refresh_token(refresh_token: str, db: AsyncSession = Depends(get_db)):
    """Refresh access token using refresh token"""
    payload = verify_token(refresh_token, token_type="refresh")
    
    user_id = payload.get("user_id")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    # Create new tokens
    token_data = {"user_id": user.id, "email": user.email}
    new_access_token = create_access_token(token_data)
    new_refresh_token = create_refresh_token(token_data)
    
    return SuccessResponse(
        data=Token(access_token=new_access_token, refresh_token=new_refresh_token),
        message="Token刷新成功"
    )


@router.post("/logout", response_model=SuccessResponse[dict])
async def logout():
    """Logout (client should discard tokens)"""
    return SuccessResponse(
        data={},
        message="登出成功"
    )

