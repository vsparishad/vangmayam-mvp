"""
API dependencies for authentication and authorization
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from jose import JWTError, jwt
from typing import Optional
import uuid

from app.core.config import settings
from app.core.database import get_db
from app.models.user import User, UserRole
from app.models.audit import UserSession

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Get current authenticated user from JWT token
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # Decode JWT token
        payload = jwt.decode(
            credentials.credentials, 
            settings.SECRET_KEY, 
            algorithms=[settings.ALGORITHM]
        )
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
            
        # Validate session
        session_result = await db.execute(
            select(UserSession).where(
                UserSession.token_hash == credentials.credentials,
                UserSession.user_id == uuid.UUID(user_id)
            )
        )
        session = session_result.scalar_one_or_none()
        
        if session is None or session.is_expired:
            raise credentials_exception
            
    except (JWTError, ValueError):
        raise credentials_exception
    
    # Get user
    user_result = await db.execute(
        select(User).where(User.id == uuid.UUID(user_id))
    )
    user = user_result.scalar_one_or_none()
    
    if user is None or not user.is_active:
        raise credentials_exception
        
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Get current active user
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Inactive user"
        )
    return current_user


async def get_admin_user(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """
    Require admin user
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    return current_user


async def get_editor_user(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """
    Require editor or admin user
    """
    if not current_user.is_editor:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Editor permissions required"
        )
    return current_user


async def get_proofreader_user(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """
    Require user who can proofread
    """
    if not current_user.can_proofread:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Proofreading permissions required"
        )
    return current_user


def require_permission(permission: str):
    """
    Dependency factory for specific permissions
    """
    async def permission_checker(
        current_user: User = Depends(get_current_active_user)
    ) -> User:
        if not current_user.has_permission(permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission '{permission}' required"
            )
        return current_user
    
    return permission_checker


# Optional user dependency (for public endpoints with optional auth)
async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False)),
    db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    """
    Get current user if authenticated, None otherwise
    """
    if not credentials:
        return None
    
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        user_id: str = payload.get("sub")
        if user_id is None:
            return None
            
        # Get user
        user_result = await db.execute(
            select(User).where(
                User.id == uuid.UUID(user_id),
                User.is_active == True
            )
        )
        return user_result.scalar_one_or_none()
        
    except (JWTError, ValueError):
        return None
