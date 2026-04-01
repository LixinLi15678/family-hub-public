"""
User and Authentication schemas
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    """Schema for user registration"""
    username: str = Field(..., min_length=2, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=100)
    family_name: Optional[str] = Field(None, max_length=100)  # For creating new family
    invite_code: Optional[str] = Field(None, max_length=20)   # For joining existing family


class UserLogin(BaseModel):
    """Schema for user login"""
    email: EmailStr
    password: str


class UserUpdate(BaseModel):
    """Schema for updating user profile"""
    username: Optional[str] = Field(None, min_length=2, max_length=50)
    avatar_url: Optional[str] = None


class UserResponse(BaseModel):
    """Schema for user response"""
    id: int
    username: str
    email: str
    family_id: Optional[int] = None
    avatar_url: Optional[str] = None
    points_balance: int = 0
    points_spent_total: int = 0
    role: str = "member"
    created_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    """Schema for JWT token response"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class AuthResponse(BaseModel):
    """Schema for authentication response (login/register)"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse


class TokenData(BaseModel):
    """Schema for decoded token data"""
    user_id: int
    email: str
    exp: Optional[datetime] = None


class DailyLoginRewardRequest(BaseModel):
    """Request to claim daily first-login reward (local date from client)"""
    local_date: str = Field(..., description="Client local date in YYYY-MM-DD")


class DailyLoginRewardResponse(BaseModel):
    """Response for daily first-login reward claim"""
    awarded: bool
    amount: int
    local_date: str
    points_balance: int
