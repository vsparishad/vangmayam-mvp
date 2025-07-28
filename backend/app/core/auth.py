"""
Authentication and Authorization for Vāṇmayam

This module provides authentication utilities for the API endpoints.
For MVP purposes, we'll use a simple current user dependency.
"""

import logging
from typing import Optional
from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..models.user import User
from .database import get_db

logger = logging.getLogger(__name__)


async def get_current_user(db: AsyncSession = Depends(get_db)) -> User:
    """
    Get current user for API endpoints.
    For MVP purposes, this returns a mock user.
    In production, this would validate JWT tokens and return the authenticated user.
    """
    try:
        # For MVP, create or get a default user
        query = select(User).where(User.email == "admin@vangmayam.org")
        result = await db.execute(query)
        user = result.scalar_one_or_none()
        
        if not user:
            # Create default admin user for MVP
            from ..models.user import UserRole
            user = User(
                email="admin@vangmayam.org",
                name="Vāṇmayam Admin",
                role=UserRole.ADMIN,
                is_active=True
            )
            db.add(user)
            await db.commit()
            await db.refresh(user)
            logger.info("✅ Created default admin user for MVP")
        
        return user
        
    except Exception as e:
        logger.error(f"❌ Error getting current user: {e}")
        # For MVP, return a mock user instead of failing
        from uuid import uuid4
        from ..models.user import UserRole
        mock_user = User(
            id=uuid4(),
            email="mvp@vangmayam.org",
            name="MVP User",
            role=UserRole.ADMIN,
            is_active=True
        )
        logger.info("✅ Using mock user for MVP testing")
        return mock_user


async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """
    Get current active user (must be active)
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    return current_user


async def get_current_superuser(current_user: User = Depends(get_current_user)) -> User:
    """
    Get current superuser (must be admin)
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Not enough permissions"
        )
    return current_user
