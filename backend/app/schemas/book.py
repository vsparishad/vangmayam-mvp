"""
Book and page schemas for manuscript management
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from decimal import Decimal
import uuid

from app.models.book import BookStatus, OCREngine


class BookBase(BaseModel):
    """Base book schema"""
    title: str = Field(..., min_length=1, max_length=500)
    author: Optional[str] = Field(None, max_length=255)
    language: str = Field(default="sanskrit", max_length=50)
    manuscript_date: Optional[date] = None
    archive_url: Optional[str] = None
    archive_id: Optional[str] = Field(None, max_length=255)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class BookCreate(BookBase):
    """Book creation schema"""
    total_pages: Optional[int] = Field(None, ge=1)


class BookUpdate(BaseModel):
    """Book update schema"""
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    author: Optional[str] = Field(None, max_length=255)
    language: Optional[str] = Field(None, max_length=50)
    manuscript_date: Optional[date] = None
    archive_url: Optional[str] = None
    archive_id: Optional[str] = Field(None, max_length=255)
    total_pages: Optional[int] = Field(None, ge=1)
    status: Optional[BookStatus] = None
    metadata: Optional[Dict[str, Any]] = None


class PageBase(BaseModel):
    """Base page schema"""
    page_number: int = Field(..., ge=1)
    image_path: str
    image_width: Optional[int] = Field(None, ge=1)
    image_height: Optional[int] = Field(None, ge=1)
    ocr_confidence: Optional[Decimal] = Field(None, ge=0, le=100)
    is_proofread: bool = False


class PageCreate(PageBase):
    """Page creation schema"""
    book_id: uuid.UUID


class PageUpdate(BaseModel):
    """Page update schema"""
    image_width: Optional[int] = Field(None, ge=1)
    image_height: Optional[int] = Field(None, ge=1)
    ocr_confidence: Optional[Decimal] = Field(None, ge=0, le=100)
    is_proofread: Optional[bool] = None


class OCRResultBase(BaseModel):
    """Base OCR result schema"""
    engine: OCREngine
    raw_text: Optional[str] = None
    alto_xml: Optional[str] = None
    confidence_data: Optional[Dict[str, Any]] = None
    word_count: Optional[int] = Field(None, ge=0)


class OCRResultCreate(OCRResultBase):
    """OCR result creation schema"""
    page_id: uuid.UUID


class OCRResultResponse(OCRResultBase):
    """OCR result response schema"""
    id: uuid.UUID
    page_id: uuid.UUID
    created_at: datetime
    
    class Config:
        from_attributes = True


class PageResponse(PageBase):
    """Page response schema"""
    id: uuid.UUID
    book_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    ocr_results: List[OCRResultResponse] = []
    
    class Config:
        from_attributes = True


class BookResponse(BookBase):
    """Book response schema"""
    id: uuid.UUID
    status: BookStatus
    total_pages: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    progress_percentage: float = 0.0
    proofread_percentage: float = 0.0
    average_confidence: float = 0.0
    
    class Config:
        from_attributes = True


class BookDetailResponse(BookResponse):
    """Detailed book response with pages"""
    pages: List[PageResponse] = []


class BookListResponse(BaseModel):
    """Paginated book list response"""
    items: List[BookResponse]
    total: int
    page: int
    size: int
    pages: int


class BookSearchRequest(BaseModel):
    """Book search request schema"""
    query: Optional[str] = None
    language: Optional[str] = None
    author: Optional[str] = None
    status: Optional[BookStatus] = None
    tags: Optional[List[str]] = None
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    
    @validator('tags')
    def validate_tags(cls, v):
        if v and len(v) > 10:
            raise ValueError('Maximum 10 tags allowed')
        return v


class BookImportRequest(BaseModel):
    """Book import request schema"""
    archive_url: str = Field(..., pattern=r'^https?://archive\.org/.+')
    title: Optional[str] = None
    author: Optional[str] = None
    language: str = "sanskrit"
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    @validator('archive_url')
    def validate_archive_url(cls, v):
        if not v.startswith(('http://archive.org/', 'https://archive.org/')):
            raise ValueError('Must be a valid archive.org URL')
        return v


class ProofreadRequest(BaseModel):
    """Proofreading request schema"""
    corrected_text: str
    confidence_notes: Optional[str] = None
    reviewer_notes: Optional[str] = None


class ExportRequest(BaseModel):
    """Export request schema"""
    format: str = Field(..., pattern=r'^(pdf|txt|rtf|epub)$')
    page_range: Optional[str] = Field(None, pattern=r'^\d+(-\d+)?(,\d+(-\d+)?)*$')
    include_images: bool = True
    include_metadata: bool = True
    
    @validator('page_range')
    def validate_page_range(cls, v):
        if v:
            # Validate page range format (e.g., "1-10,15,20-25")
            parts = v.split(',')
            for part in parts:
                if '-' in part:
                    start, end = part.split('-', 1)
                    if not (start.isdigit() and end.isdigit() and int(start) <= int(end)):
                        raise ValueError('Invalid page range format')
                elif not part.isdigit():
                    raise ValueError('Invalid page range format')
        return v
