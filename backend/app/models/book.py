"""
Book, Page, and OCR models for manuscript management
"""

from sqlalchemy import Column, String, Integer, Text, Boolean, DateTime, ForeignKey, Enum, DECIMAL
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
import enum

from app.core.database import Base


class BookStatus(str, enum.Enum):
    """Book processing status"""
    IMPORTED = "imported"
    PROCESSING = "processing"
    OCR_COMPLETE = "ocr_complete"
    PROOFREAD = "proofread"
    PUBLISHED = "published"


class OCREngine(str, enum.Enum):
    """OCR engine types"""
    TESSERACT = "tesseract"
    GOOGLE_VISION = "google_vision"
    EASYOCR = "easyocr"


class Book(Base):
    """Book/manuscript model"""
    
    __tablename__ = "books"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(500), nullable=False, index=True)
    author = Column(String(255), nullable=True)
    language = Column(String(50), default="sanskrit", nullable=False, index=True)
    manuscript_date = Column(DateTime, nullable=True)
    archive_url = Column(Text, nullable=True)
    archive_id = Column(String(255), nullable=True, index=True)
    total_pages = Column(Integer, nullable=True)
    status = Column(Enum(BookStatus), default=BookStatus.IMPORTED, nullable=False, index=True)
    book_metadata = Column(JSONB, default=dict, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    pages = relationship("Page", back_populates="book", cascade="all, delete-orphan")
    tags = relationship("BookTag", back_populates="book", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Book(title='{self.title}', status='{self.status}')>"
    
    @property
    def progress_percentage(self) -> float:
        """Calculate processing progress"""
        if not self.total_pages or self.total_pages == 0:
            return 0.0
        
        processed_pages = len([p for p in self.pages if p.ocr_results])
        return (processed_pages / self.total_pages) * 100
    
    @property
    def proofread_percentage(self) -> float:
        """Calculate proofreading progress"""
        if not self.pages:
            return 0.0
        
        proofread_pages = len([p for p in self.pages if p.is_proofread])
        return (proofread_pages / len(self.pages)) * 100
    
    @property
    def average_confidence(self) -> float:
        """Calculate average OCR confidence"""
        if not self.pages:
            return 0.0
        
        confidences = [p.ocr_confidence for p in self.pages if p.ocr_confidence]
        return sum(confidences) / len(confidences) if confidences else 0.0


class Page(Base):
    """Individual page model"""
    
    __tablename__ = "pages"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    book_id = Column(UUID(as_uuid=True), ForeignKey("books.id"), nullable=False)
    page_number = Column(Integer, nullable=False)
    image_path = Column(Text, nullable=False)
    image_width = Column(Integer, nullable=True)
    image_height = Column(Integer, nullable=True)
    ocr_confidence = Column(DECIMAL(5, 2), nullable=True)
    is_proofread = Column(Boolean, default=False, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    book = relationship("Book", back_populates="pages")
    ocr_results = relationship("OCRResult", back_populates="page", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Page(book_id='{self.book_id}', page_number={self.page_number})>"
    
    @property
    def best_ocr_result(self) -> 'OCRResult':
        """Get the OCR result with highest confidence"""
        if not self.ocr_results:
            return None
        
        return max(self.ocr_results, key=lambda x: x.confidence_data.get('overall', 0) if x.confidence_data else 0)
    
    @property
    def has_multiple_ocr(self) -> bool:
        """Check if page has multiple OCR results"""
        return len(self.ocr_results) > 1


class OCRResult(Base):
    """OCR processing results"""
    
    __tablename__ = "ocr_results"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    page_id = Column(UUID(as_uuid=True), ForeignKey("pages.id"), nullable=False)
    engine = Column(Enum(OCREngine), nullable=False)
    raw_text = Column(Text, nullable=True)
    alto_xml = Column(Text, nullable=True)
    confidence_data = Column(JSONB, nullable=True)
    word_count = Column(Integer, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    page = relationship("Page", back_populates="ocr_results")
    
    def __repr__(self):
        return f"<OCRResult(page_id='{self.page_id}', engine='{self.engine}')>"
    
    @property
    def overall_confidence(self) -> float:
        """Get overall confidence score"""
        if not self.confidence_data:
            return 0.0
        return self.confidence_data.get('overall', 0.0)
    
    @property
    def word_confidences(self) -> list:
        """Get word-level confidence scores"""
        if not self.confidence_data:
            return []
        return self.confidence_data.get('words', [])
    
    def get_low_confidence_words(self, threshold: float = 0.7) -> list:
        """Get words below confidence threshold"""
        words = self.word_confidences
        return [w for w in words if w.get('confidence', 0) < threshold]
