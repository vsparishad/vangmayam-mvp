"""
Authentication endpoints for Google OAuth 2.0 and JWT
Complete implementation with detailed Google Cloud Console integration
"""

from fastapi import APIRouter, HTTPException, Depends, status, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import RedirectResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional, Dict, Any
import logging
from datetime import datetime

from ....core.database import get_db
from ....models.user import User
from ....core.auth import get_current_user
from ....services.google_auth_service import google_auth_service, AuthTokens, GoogleUserInfo

logger = logging.getLogger(__name__)

router = APIRouter()

# Security scheme
security = HTTPBearer()

# Pydantic models for request/response

class AuthResponse(BaseModel):
    """Authentication response model"""
    user: Dict[str, Any]
    tokens: AuthTokens
    message: str

class AuthStatus(BaseModel):
    """Authentication status model"""
    authenticated: bool
    user: Optional[Dict[str, Any]] = None
    google_oauth_configured: bool
    auth_url: Optional[str] = None

@router.get("/status")
async def get_auth_status() -> AuthStatus:
    """
    Get authentication system status and configuration
    """
    try:
        logger.info("📊 Checking authentication system status")
        
        # Check if Google OAuth is configured
        is_configured = google_auth_service.config.is_configured()
        
        auth_url = None
        if is_configured:
            try:
                auth_url, _ = google_auth_service.generate_auth_url()
            except Exception as e:
                logger.warning(f"⚠️ Could not generate auth URL: {e}")
        
        status = AuthStatus(
            authenticated=False,
            google_oauth_configured=is_configured,
            auth_url=auth_url
        )
        
        logger.info(f"✅ Auth status: OAuth configured={is_configured}")
        return status
        
    except Exception as e:
        logger.error(f"❌ Error getting auth status: {e}")
        raise HTTPException(status_code=500, detail=f"Auth status check failed: {str(e)}")

@router.get("/google/login")
async def google_login(redirect_url: Optional[str] = Query(None, description="Frontend redirect URL after auth")):
    """
    Initiate Google OAuth 2.0 login flow
    """
    try:
        logger.info("🔐 Initiating Google OAuth login flow")
        
        if not google_auth_service.config.is_configured():
            raise HTTPException(
                status_code=500, 
                detail="Google OAuth not configured. Please set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET environment variables."
            )
        
        # Generate authorization URL
        auth_url, state = google_auth_service.generate_auth_url()
        
        # Store redirect URL in session if provided
        if redirect_url:
            google_auth_service.session_store[state]['redirect_url'] = redirect_url
        
        logger.info("✅ Generated Google OAuth authorization URL")
        
        # Return JSON response with auth URL for frontend
        return {
            "auth_url": auth_url,
            "state": state,
            "message": "Redirect to auth_url to complete Google login"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Google login initiation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Login initiation failed: {str(e)}")

@router.get("/google/callback")
async def google_callback(
    code: str = Query(..., description="Authorization code from Google"),
    state: str = Query(..., description="State parameter for CSRF protection"),
    error: Optional[str] = Query(None, description="Error from Google OAuth"),
    db: AsyncSession = Depends(get_db)
):
    """
    Handle Google OAuth 2.0 callback
    """
    try:
        logger.info("🔄 Processing Google OAuth callback")
        
        # Check for OAuth errors
        if error:
            logger.error(f"❌ Google OAuth error: {error}")
            raise HTTPException(status_code=400, detail=f"OAuth error: {error}")
        
        if not code:
            raise HTTPException(status_code=400, detail="Missing authorization code")
        
        if not state:
            raise HTTPException(status_code=400, detail="Missing state parameter")
        
        # Complete authentication
        user, tokens = await google_auth_service.authenticate_user(code, state, db)
        
        # Get redirect URL from session store
        redirect_url = None
        if state in google_auth_service.session_store:
            redirect_url = google_auth_service.session_store[state].get('redirect_url')
        
        # Clean up session store
        if state in google_auth_service.session_store:
            del google_auth_service.session_store[state]
        
        # Prepare response data
        auth_response = AuthResponse(
            user={
                "id": user.id,
                "email": user.email,
                "name": user.name,
                "role": user.role.value,
                "is_active": user.is_active
            },
            tokens=tokens,
            message="Authentication successful"
        )
        
        logger.info(f"✅ Google OAuth authentication successful for: {user.email}")
        
        # If redirect URL provided, redirect to frontend with token
        if redirect_url:
            # Append token to redirect URL
            separator = "&" if "?" in redirect_url else "?"
            redirect_with_token = f"{redirect_url}{separator}token={tokens.access_token}&user_id={user.id}"
            return RedirectResponse(url=redirect_with_token)
        
        # Otherwise return JSON response
        return auth_response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Google OAuth callback failed: {e}")
        raise HTTPException(status_code=500, detail=f"Authentication failed: {str(e)}")

@router.post("/logout")
async def logout(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
):
    """
    Logout user and invalidate token
    """
    try:
        logger.info("🚪 Processing user logout")
        
        token = credentials.credentials
        
        # Verify token and get user
        user = await google_auth_service.get_current_user_from_token(token, db)
        
        if user:
            logger.info(f"✅ Logout successful for user: {user.email}")
        else:
            logger.info("✅ Logout processed (token was invalid)")
        
        # In production, you would add token to blacklist
        # For now, we'll just return success
        
        return {
            "message": "Logout successful",
            "logged_out_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Logout failed: {e}")
        raise HTTPException(status_code=500, detail=f"Logout failed: {str(e)}")

@router.get("/me")
async def get_current_user_info(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get current authenticated user information
    """
    try:
        logger.info(f"👤 Getting user info for: {current_user.email}")
        
        user_info = {
            "id": current_user.id,
            "email": current_user.email,
            "name": current_user.name,
            "role": current_user.role.value,
            "is_active": current_user.is_active,
            "google_id": current_user.google_id,
            "created_at": current_user.created_at.isoformat() if current_user.created_at else None,
            "updated_at": current_user.updated_at.isoformat() if current_user.updated_at else None
        }
        
        logger.info("✅ User info retrieved successfully")
        return user_info
        
    except Exception as e:
        logger.error(f"❌ Error getting user info: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get user info: {str(e)}")

@router.post("/verify-token")
async def verify_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
):
    """
    Verify JWT token and return user information
    """
    try:
        logger.info("🔍 Verifying JWT token")
        
        token = credentials.credentials
        
        # Get user from token
        user = await google_auth_service.get_current_user_from_token(token, db)
        
        if not user:
            raise HTTPException(status_code=401, detail="Invalid or expired token")
        
        user_info = {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "role": user.role.value,
            "is_active": user.is_active
        }
        
        logger.info(f"✅ Token verified for user: {user.email}")
        return {
            "valid": True,
            "user": user_info,
            "verified_at": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Token verification failed: {e}")
        raise HTTPException(status_code=500, detail=f"Token verification failed: {str(e)}")

@router.get("/test/mock-login")
async def mock_login_for_testing(
    email: str = Query("admin@vangmayam.org", description="Email for mock user"),
    db: AsyncSession = Depends(get_db)
):
    """
    Mock login endpoint for development and testing (remove in production)
    """
    try:
        logger.info(f"🧪 Mock login for testing: {email}")
        
        # This is for development only - remove in production
        from ....models.user import UserRole
        from sqlalchemy import select
        
        # Check if user exists
        query = select(User).where(User.email == email)
        result = await db.execute(query)
        user = result.scalar_one_or_none()
        
        if not user:
            # Create mock user
            from ....models.user import UserRole
            role = UserRole.ADMIN if "admin" in email.lower() else UserRole.READER
            user = User(
                email=email,
                name="Mock User",
                role=role,
                is_active=True
            )
            db.add(user)
            await db.commit()
            await db.refresh(user)
        
        # Create JWT token
        token_data = {
            "sub": str(user.id),
            "email": user.email,
            "role": user.role.value
        }
        
        jwt_token = google_auth_service.create_access_token(token_data)
        
        tokens = AuthTokens(
            access_token=jwt_token,
            expires_in=30 * 60  # 30 minutes
        )
        
        auth_response = AuthResponse(
            user={
                "id": user.id,
                "email": user.email,
                "name": user.name,
                "role": user.role.value,
                "is_active": user.is_active
            },
            tokens=tokens,
            message="Mock authentication successful (development only)"
        )
        
        logger.info(f"✅ Mock login successful for: {user.email}")
        return auth_response

    except Exception as e:
        logger.error(f"❌ Mock login failed: {e}")
        raise HTTPException(status_code=500, detail=f"Mock login failed: {str(e)}")
