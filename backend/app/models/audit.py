"""
Audit and session models for security and tracking
"""

from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB, INET
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from app.core.database import Base


class UserSession(Base):
    """User session model for JWT token management"""
    
    __tablename__ = "user_sessions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    token_hash = Column(String(255), nullable=False, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    
    def __repr__(self):
        return f"<UserSession(user_id='{self.user_id}', expires_at='{self.expires_at}')>"
    
    @property
    def is_expired(self) -> bool:
        """Check if session is expired"""
        from datetime import datetime, timezone
        return datetime.now(timezone.utc) > self.expires_at


class AuditLog(Base):
    """Audit log model for tracking user actions"""
    
    __tablename__ = "audit_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    action = Column(String(100), nullable=False, index=True)
    resource_type = Column(String(50), nullable=True, index=True)
    resource_id = Column(UUID(as_uuid=True), nullable=True)
    details = Column(JSONB, nullable=True)
    ip_address = Column(INET, nullable=True)
    user_agent = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    
    def __repr__(self):
        return f"<AuditLog(action='{self.action}', resource_type='{self.resource_type}')>"
    
    @classmethod
    def create_log(cls, user_id: uuid.UUID = None, action: str = None, 
                   resource_type: str = None, resource_id: uuid.UUID = None,
                   details: dict = None, ip_address: str = None, 
                   user_agent: str = None) -> 'AuditLog':
        """Create a new audit log entry"""
        return cls(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details or {},
            ip_address=ip_address,
            user_agent=user_agent
        )
