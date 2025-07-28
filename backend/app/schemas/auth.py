"""
Authentication schemas for request/response validation
"""

from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime
import uuid

from app.models.user import UserRole


class UserBase(BaseModel):
    """Base user schema"""
    email: EmailStr
    name: str
    role: UserRole = UserRole.READER
    is_active: bool = True


class UserCreate(UserBase):
    """User creation schema"""
    google_id: Optional[str] = None


class UserUpdate(BaseModel):
    """User update schema"""
    name: Optional[str] = None
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None


class UserResponse(UserBase):
    """User response schema"""
    id: uuid.UUID
    google_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    """Token response schema"""
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class LoginRequest(BaseModel):
    """Login request schema"""
    email: EmailStr
    password: str


class GoogleAuthRequest(BaseModel):
    """Google auth request schema"""
    id_token: str
