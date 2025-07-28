"""
Books API endpoints for manuscript management
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload
from typing import List, Optional
import uuid

from app.core.database import get_db
from app.models.book import Book, Page, OCRResult, BookStatus
from app.models.user import User
from app.models.audit import AuditLog
from app.api.deps import get_current_user, get_editor_user, get_optional_user
from app.schemas.book import (
    BookResponse, BookDetailResponse, BookListResponse, BookCreate, 
    BookUpdate, BookSearchRequest, BookImportRequest, PageResponse,
    ProofreadRequest, ExportRequest
)

router = APIRouter()


@router.get("/", response_model=BookListResponse)
async def list_books(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    language: Optional[str] = Query(None),
    status: Optional[BookStatus] = Query(None),
    author: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    """List books with pagination and filtering"""
    
    # Build query
    query = select(Book)
    
    # Apply filters
    filters = []
    if language:
        filters.append(Book.language == language)
    if status:
        filters.append(Book.status == status)
    if author:
        filters.append(Book.author.ilike(f"%{author}%"))
    if search:
        filters.append(or_(
            Book.title.ilike(f"%{search}%"),
            Book.author.ilike(f"%{search}%")
        ))
    
    if filters:
        query = query.where(and_(*filters))
    
    # Get total count
    count_query = select(func.count()).select_from(Book)
    if filters:
        count_query = count_query.where(and_(*filters))
    
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Apply pagination
    offset = (page - 1) * size
    query = query.offset(offset).limit(size).order_by(Book.created_at.desc())
    
    result = await db.execute(query)
    books = result.scalars().all()
    
    return BookListResponse(
        items=[BookResponse.from_orm(book) for book in books],
        total=total,
        page=page,
        size=size,
        pages=(total + size - 1) // size
    )


@router.post("/", response_model=BookResponse)
async def create_book(
    book_data: BookCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_editor_user)
):
    """Create a new book"""
    
    book = Book(**book_data.dict())
    db.add(book)
    await db.commit()
    await db.refresh(book)
    
    # Log creation
    audit_log = AuditLog.create_log(
        user_id=current_user.id,
        action="create",
        resource_type="book",
        resource_id=book.id,
        details={"title": book.title}
    )
    db.add(audit_log)
    await db.commit()
    
    return BookResponse.from_orm(book)


@router.get("/{book_id}", response_model=BookDetailResponse)
async def get_book(
    book_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    """Get book details with pages"""
    
    query = select(Book).options(
        selectinload(Book.pages).selectinload(Page.ocr_results)
    ).where(Book.id == book_id)
    
    result = await db.execute(query)
    book = result.scalar_one_or_none()
    
    if not book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Book not found"
        )
    
    return BookDetailResponse.from_orm(book)


@router.put("/{book_id}", response_model=BookResponse)
async def update_book(
    book_id: uuid.UUID,
    book_data: BookUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_editor_user)
):
    """Update book information"""
    
    result = await db.execute(select(Book).where(Book.id == book_id))
    book = result.scalar_one_or_none()
    
    if not book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Book not found"
        )
    
    # Update fields
    update_data = book_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(book, field, value)
    
    await db.commit()
    await db.refresh(book)
    
    # Log update
    audit_log = AuditLog.create_log(
        user_id=current_user.id,
        action="update",
        resource_type="book",
        resource_id=book.id,
        details={"updated_fields": list(update_data.keys())}
    )
    db.add(audit_log)
    await db.commit()
    
    return BookResponse.from_orm(book)


@router.delete("/{book_id}")
async def delete_book(
    book_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_editor_user)
):
    """Delete a book"""
    
    result = await db.execute(select(Book).where(Book.id == book_id))
    book = result.scalar_one_or_none()
    
    if not book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Book not found"
        )
    
    # Log deletion before deleting
    audit_log = AuditLog.create_log(
        user_id=current_user.id,
        action="delete",
        resource_type="book",
        resource_id=book.id,
        details={"title": book.title}
    )
    db.add(audit_log)
    
    await db.delete(book)
    await db.commit()
    
    return {"message": "Book deleted successfully"}


@router.post("/import", response_model=BookResponse)
async def import_book(
    import_data: BookImportRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_editor_user)
):
    """Import book from archive.org"""
    
    # Create book record
    book = Book(
        title=import_data.title or "Imported Book",
        author=import_data.author,
        language=import_data.language,
        archive_url=import_data.archive_url,
        status=BookStatus.IMPORTED,
        metadata=import_data.metadata
    )
    
    db.add(book)
    await db.commit()
    await db.refresh(book)
    
    # TODO: Trigger async import task
    # This would be handled by Celery in production
    
    # Log import
    audit_log = AuditLog.create_log(
        user_id=current_user.id,
        action="import",
        resource_type="book",
        resource_id=book.id,
        details={"archive_url": import_data.archive_url}
    )
    db.add(audit_log)
    await db.commit()
    
    return BookResponse.from_orm(book)


@router.post("/{book_id}/upload", response_model=BookResponse)
async def upload_book_file(
    book_id: uuid.UUID,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_editor_user)
):
    """Upload PDF file for a book"""
    
    # Validate file type
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are allowed"
        )
    
    result = await db.execute(select(Book).where(Book.id == book_id))
    book = result.scalar_one_or_none()
    
    if not book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Book not found"
        )
    
    # TODO: Save file and trigger processing
    # This would involve:
    # 1. Save file to storage (MinIO)
    # 2. Trigger PDF to image conversion
    # 3. Start OCR processing
    
    book.status = BookStatus.PROCESSING
    await db.commit()
    
    return BookResponse.from_orm(book)


@router.get("/{book_id}/pages", response_model=List[PageResponse])
async def get_book_pages(
    book_id: uuid.UUID,
    page_start: int = Query(1, ge=1),
    page_end: Optional[int] = Query(None, ge=1),
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    """Get pages for a book"""
    
    query = select(Page).options(
        selectinload(Page.ocr_results)
    ).where(Page.book_id == book_id)
    
    if page_end:
        query = query.where(
            and_(
                Page.page_number >= page_start,
                Page.page_number <= page_end
            )
        )
    else:
        query = query.where(Page.page_number >= page_start)
    
    query = query.order_by(Page.page_number)
    
    result = await db.execute(query)
    pages = result.scalars().all()
    
    return [PageResponse.from_orm(page) for page in pages]


@router.post("/{book_id}/pages/{page_id}/proofread")
async def proofread_page(
    book_id: uuid.UUID,
    page_id: uuid.UUID,
    proofread_data: ProofreadRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Submit proofreading for a page"""
    
    if not current_user.can_proofread:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Proofreading permissions required"
        )
    
    result = await db.execute(
        select(Page).where(
            and_(Page.id == page_id, Page.book_id == book_id)
        )
    )
    page = result.scalar_one_or_none()
    
    if not page:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Page not found"
        )
    
    # TODO: Update OCR result with corrected text
    # This would involve creating a new OCR result or updating existing one
    
    page.is_proofread = True
    await db.commit()
    
    # Log proofreading
    audit_log = AuditLog.create_log(
        user_id=current_user.id,
        action="proofread",
        resource_type="page",
        resource_id=page.id,
        details={"book_id": str(book_id), "page_number": page.page_number}
    )
    db.add(audit_log)
    await db.commit()
    
    return {"message": "Proofreading submitted successfully"}


@router.post("/{book_id}/export")
async def export_book(
    book_id: uuid.UUID,
    export_data: ExportRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Export book in specified format"""
    
    result = await db.execute(select(Book).where(Book.id == book_id))
    book = result.scalar_one_or_none()
    
    if not book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Book not found"
        )
    
    # TODO: Generate export file
    # This would be handled by a background task
    
    # Log export
    audit_log = AuditLog.create_log(
        user_id=current_user.id,
        action="export",
        resource_type="book",
        resource_id=book.id,
        details={
            "format": export_data.format,
            "page_range": export_data.page_range
        }
    )
    db.add(audit_log)
    await db.commit()
    
    return {"message": f"Export started for {export_data.format} format"}
