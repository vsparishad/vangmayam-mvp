"""
Tag models for content categorization
"""

from sqlalchemy import Column, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from app.core.database import Base


class Tag(Base):
    """Tag model for categorizing books"""
    
    __tablename__ = "tags"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    category = Column(String(50), nullable=True, index=True)
    is_approved = Column(Boolean, default=False, nullable=False)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    creator = relationship("User", foreign_keys=[created_by])
    book_tags = relationship("BookTag", back_populates="tag", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Tag(name='{self.name}', category='{self.category}')>"
    
    @property
    def usage_count(self) -> int:
        """Get number of books using this tag"""
        return len(self.book_tags)


class BookTag(Base):
    """Junction table for book-tag relationships"""
    
    __tablename__ = "book_tags"
    
    book_id = Column(UUID(as_uuid=True), ForeignKey("books.id"), primary_key=True)
    tag_id = Column(UUID(as_uuid=True), ForeignKey("tags.id"), primary_key=True)
    added_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    added_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    book = relationship("Book", back_populates="tags")
    tag = relationship("Tag", back_populates="book_tags")
    user = relationship("User", foreign_keys=[added_by])
    
    def __repr__(self):
        return f"<BookTag(book_id='{self.book_id}', tag_id='{self.tag_id}')>"
