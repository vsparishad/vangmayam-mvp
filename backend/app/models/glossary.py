"""
Glossary model for Sanskrit dictionary integration
"""

from sqlalchemy import Column, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from app.core.database import Base


class GlossaryEntry(Base):
    """Glossary/dictionary entry model"""
    
    __tablename__ = "glossary_entries"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    word = Column(String(255), nullable=False, index=True)
    definition = Column(Text, nullable=False)
    etymology = Column(Text, nullable=True)
    pronunciation = Column(String(255), nullable=True)
    language = Column(String(50), default="sanskrit", nullable=False, index=True)
    source = Column(String(255), nullable=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    is_verified = Column(Boolean, default=False, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    creator = relationship("User", foreign_keys=[created_by])
    
    def __repr__(self):
        return f"<GlossaryEntry(word='{self.word}', language='{self.language}')>"
    
    @property
    def is_sanskrit(self) -> bool:
        """Check if entry is Sanskrit"""
        return self.language == "sanskrit"
    
    @property
    def has_pronunciation(self) -> bool:
        """Check if entry has pronunciation guide"""
        return bool(self.pronunciation)
    
    def get_romanized_word(self) -> str:
        """Get romanized version of Sanskrit word"""
        # This would integrate with transliteration library
        # For now, return the word as-is
        return self.word
