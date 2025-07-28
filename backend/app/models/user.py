"""
User model for authentication and authorization
"""

from sqlalchemy import Column, String, Boolean, DateTime, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid
import enum

from app.core.database import Base


class UserRole(str, enum.Enum):
    """User roles enum"""
    ADMIN = "admin"
    EDITOR = "editor" 
    READER = "reader"
    SCHOLAR = "scholar"


class User(Base):
    """User model"""
    
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), default=UserRole.READER, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    google_id = Column(String(255), unique=True, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    def __repr__(self):
        return f"<User(email='{self.email}', role='{self.role}')>"
    
    @property
    def is_admin(self) -> bool:
        """Check if user is admin"""
        return self.role == UserRole.ADMIN
    
    @property
    def is_editor(self) -> bool:
        """Check if user can edit content"""
        return self.role in [UserRole.ADMIN, UserRole.EDITOR]
    
    @property
    def can_proofread(self) -> bool:
        """Check if user can proofread OCR"""
        return self.role in [UserRole.ADMIN, UserRole.EDITOR, UserRole.SCHOLAR]
    
    def has_permission(self, permission: str) -> bool:
        """Check if user has specific permission"""
        permissions = {
            UserRole.ADMIN: [
                "manage_users", "manage_books", "manage_tags", 
                "proofread", "export", "view_audit_logs"
            ],
            UserRole.EDITOR: [
                "manage_books", "manage_tags", "proofread", "export"
            ],
            UserRole.SCHOLAR: [
                "proofread", "export", "advanced_search"
            ],
            UserRole.READER: [
                "view_books", "basic_search", "export"
            ]
        }
        
        return permission in permissions.get(self.role, [])
