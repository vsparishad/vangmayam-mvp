"""
Google OAuth 2.0 Authentication Service for Vāṇmayam

This module provides comprehensive Google OAuth 2.0 authentication including:
- OAuth 2.0 authorization flow
- Google user profile retrieval
- JWT token generation and validation
- User creation and management
- Integration with existing user system
"""

import asyncio
import logging
import secrets
import json
from typing import Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from urllib.parse import urlencode, parse_qs
import aiohttp

from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from ..models.user import User, UserRole
from ..core.database import get_db
from ..core.config import settings

logger = logging.getLogger(__name__)

# JWT and password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30


class GoogleAuthConfig:
    """Google OAuth 2.0 configuration"""
    
    def __init__(self):
        # These should be set in environment variables
        self.client_id = getattr(settings, 'GOOGLE_CLIENT_ID', '')
        self.client_secret = getattr(settings, 'GOOGLE_CLIENT_SECRET', '')
        self.redirect_uri = getattr(settings, 'GOOGLE_REDIRECT_URI', 'http://localhost:8001/api/v1/auth/google/callback')
        
        # Google OAuth 2.0 endpoints
        self.auth_uri = "https://accounts.google.com/o/oauth2/auth"
        self.token_uri = "https://oauth2.googleapis.com/token"
        self.userinfo_uri = "https://www.googleapis.com/oauth2/v2/userinfo"
        
        # OAuth 2.0 scopes
        self.scopes = [
            "openid",
            "https://www.googleapis.com/auth/userinfo.email",
            "https://www.googleapis.com/auth/userinfo.profile"
        ]
    
    def is_configured(self) -> bool:
        """Check if Google OAuth is properly configured"""
        return bool(self.client_id and self.client_secret)


class GoogleUserInfo(BaseModel):
    """Google user information model"""
    id: str
    email: str
    verified_email: bool
    name: str
    given_name: Optional[str] = None
    family_name: Optional[str] = None
    picture: Optional[str] = None
    locale: Optional[str] = None


class AuthTokens(BaseModel):
    """Authentication tokens model"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    refresh_token: Optional[str] = None


class GoogleAuthService:
    """
    Google OAuth 2.0 authentication service
    """
    
    def __init__(self):
        self.config = GoogleAuthConfig()
        self.session_store = {}  # In-memory session store (use Redis in production)
    
    def generate_auth_url(self, state: Optional[str] = None) -> Tuple[str, str]:
        """
        Generate Google OAuth 2.0 authorization URL
        """
        try:
            if not self.config.is_configured():
                raise ValueError("Google OAuth 2.0 not configured. Please set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET.")
            
            # Generate state parameter for CSRF protection
            if not state:
                state = secrets.token_urlsafe(32)
            
            # Store state in session store
            self.session_store[state] = {
                'created_at': datetime.utcnow(),
                'used': False
            }
            
            # Build authorization URL
            params = {
                'client_id': self.config.client_id,
                'redirect_uri': self.config.redirect_uri,
                'scope': ' '.join(self.config.scopes),
                'response_type': 'code',
                'state': state,
                'access_type': 'offline',
                'prompt': 'consent'
            }
            
            auth_url = f"{self.config.auth_uri}?{urlencode(params)}"
            
            logger.info(f"🔗 Generated Google OAuth authorization URL")
            return auth_url, state
            
        except Exception as e:
            logger.error(f"❌ Error generating auth URL: {e}")
            raise
    
    def validate_state(self, state: str) -> bool:
        """
        Validate OAuth state parameter
        """
        try:
            if state not in self.session_store:
                logger.warning(f"⚠️ Invalid OAuth state: {state}")
                return False
            
            session = self.session_store[state]
            
            # Check if already used
            if session['used']:
                logger.warning(f"⚠️ OAuth state already used: {state}")
                return False
            
            # Check expiration (5 minutes)
            if datetime.utcnow() - session['created_at'] > timedelta(minutes=5):
                logger.warning(f"⚠️ OAuth state expired: {state}")
                del self.session_store[state]
                return False
            
            # Mark as used
            session['used'] = True
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error validating state: {e}")
            return False
    
    async def exchange_code_for_tokens(self, code: str) -> Dict[str, Any]:
        """
        Exchange authorization code for access tokens
        """
        try:
            if not self.config.is_configured():
                raise ValueError("Google OAuth 2.0 not configured")
            
            # Prepare token request
            data = {
                'client_id': self.config.client_id,
                'client_secret': self.config.client_secret,
                'code': code,
                'grant_type': 'authorization_code',
                'redirect_uri': self.config.redirect_uri
            }
            
            # Exchange code for tokens
            async with aiohttp.ClientSession() as session:
                async with session.post(self.config.token_uri, data=data) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"❌ Token exchange failed: {response.status} - {error_text}")
                        raise ValueError(f"Token exchange failed: {response.status}")
                    
                    tokens = await response.json()
            
            logger.info("✅ Successfully exchanged code for tokens")
            return tokens
            
        except Exception as e:
            logger.error(f"❌ Error exchanging code for tokens: {e}")
            raise
    
    async def get_user_info(self, access_token: str) -> GoogleUserInfo:
        """
        Get user information from Google using access token
        """
        try:
            headers = {
                'Authorization': f'Bearer {access_token}'
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(self.config.userinfo_uri, headers=headers) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"❌ User info request failed: {response.status} - {error_text}")
                        raise ValueError(f"User info request failed: {response.status}")
                    
                    user_data = await response.json()
            
            user_info = GoogleUserInfo(**user_data)
            logger.info(f"✅ Retrieved user info for: {user_info.email}")
            return user_info
            
        except Exception as e:
            logger.error(f"❌ Error getting user info: {e}")
            raise
    
    async def create_or_update_user(self, user_info: GoogleUserInfo, db: AsyncSession) -> User:
        """
        Create or update user based on Google user info
        """
        try:
            # Check if user exists
            query = select(User).where(User.google_id == user_info.id)
            result = await db.execute(query)
            user = result.scalar_one_or_none()
            
            if user:
                # Update existing user
                user.email = user_info.email
                user.name = user_info.name
                user.is_active = True
                user.updated_at = datetime.utcnow()
                
                logger.info(f"✅ Updated existing user: {user_info.email}")
            else:
                # Check if user exists with same email
                email_query = select(User).where(User.email == user_info.email)
                email_result = await db.execute(email_query)
                existing_user = email_result.scalar_one_or_none()
                
                if existing_user:
                    # Link Google account to existing user
                    existing_user.google_id = user_info.id
                    existing_user.name = user_info.name
                    existing_user.is_active = True
                    existing_user.updated_at = datetime.utcnow()
                    user = existing_user
                    
                    logger.info(f"✅ Linked Google account to existing user: {user_info.email}")
                else:
                    # Create new user
                    user = User(
                        email=user_info.email,
                        name=user_info.name,
                        google_id=user_info.id,
                        role=UserRole.USER,  # Default role
                        is_active=True
                    )
                    db.add(user)
                    
                    logger.info(f"✅ Created new user: {user_info.email}")
            
            await db.commit()
            await db.refresh(user)
            
            return user
            
        except Exception as e:
            await db.rollback()
            logger.error(f"❌ Error creating/updating user: {e}")
            raise
    
    def create_access_token(self, data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        """
        Create JWT access token
        """
        try:
            to_encode = data.copy()
            
            if expires_delta:
                expire = datetime.utcnow() + expires_delta
            else:
                expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
            
            to_encode.update({"exp": expire})
            
            # Use a secret key from settings (should be set in environment)
            secret_key = getattr(settings, 'SECRET_KEY', 'your-secret-key-change-in-production')
            encoded_jwt = jwt.encode(to_encode, secret_key, algorithm=ALGORITHM)
            
            logger.info("✅ Created JWT access token")
            return encoded_jwt
            
        except Exception as e:
            logger.error(f"❌ Error creating access token: {e}")
            raise
    
    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Verify JWT token and return payload
        """
        try:
            secret_key = getattr(settings, 'SECRET_KEY', 'your-secret-key-change-in-production')
            payload = jwt.decode(token, secret_key, algorithms=[ALGORITHM])
            
            return payload
            
        except JWTError as e:
            logger.warning(f"⚠️ Invalid JWT token: {e}")
            return None
        except Exception as e:
            logger.error(f"❌ Error verifying token: {e}")
            return None
    
    async def authenticate_user(self, code: str, state: str, db: AsyncSession) -> Tuple[User, AuthTokens]:
        """
        Complete OAuth authentication flow
        """
        try:
            logger.info("🔐 Starting Google OAuth authentication flow")
            
            # Validate state parameter
            if not self.validate_state(state):
                raise ValueError("Invalid or expired state parameter")
            
            # Exchange code for tokens
            tokens = await self.exchange_code_for_tokens(code)
            access_token = tokens.get('access_token')
            
            if not access_token:
                raise ValueError("No access token received from Google")
            
            # Get user information
            user_info = await self.get_user_info(access_token)
            
            # Create or update user
            user = await self.create_or_update_user(user_info, db)
            
            # Create JWT tokens
            token_data = {
                "sub": str(user.id),
                "email": user.email,
                "role": user.role.value
            }
            
            jwt_token = self.create_access_token(token_data)
            
            auth_tokens = AuthTokens(
                access_token=jwt_token,
                expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
                refresh_token=tokens.get('refresh_token')
            )
            
            logger.info(f"✅ Authentication successful for user: {user.email}")
            return user, auth_tokens
            
        except Exception as e:
            logger.error(f"❌ Authentication failed: {e}")
            raise
    
    async def get_current_user_from_token(self, token: str, db: AsyncSession) -> Optional[User]:
        """
        Get current user from JWT token
        """
        try:
            payload = self.verify_token(token)
            if not payload:
                return None
            
            user_id = payload.get("sub")
            if not user_id:
                return None
            
            query = select(User).where(User.id == int(user_id))
            result = await db.execute(query)
            user = result.scalar_one_or_none()
            
            if user and user.is_active:
                return user
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Error getting current user: {e}")
            return None


# Global service instance
google_auth_service = GoogleAuthService()
