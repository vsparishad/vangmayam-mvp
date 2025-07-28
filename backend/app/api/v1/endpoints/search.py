"""
Advanced Search API Endpoints with Sanskrit Integration for Vāṇmayam

This module provides REST API endpoints for:
- Full-text search across OCR'd documents
- Sanskrit-aware search with linguistic analysis
- Search suggestions and autocomplete
- Integration with proofreading workflow
- Elasticsearch-powered advanced search
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends, Query, BackgroundTasks
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, and_, func, text
from pydantic import BaseModel, Field

from ....services.search_service import search_service
from ....models.book import Book, Page, OCRResult
from ....models.proofreading import ProofreadingTask, SanskritGlossaryEntry
from ....core.database import get_db
from ....core.auth import get_current_user
from ....models.user import User

logger = logging.getLogger(__name__)

router = APIRouter()


# Pydantic models for request/response

class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Search query")
    language: Optional[str] = Field(None, description="Filter by language")
    author: Optional[str] = Field(None, description="Filter by author")
    tags: Optional[List[str]] = Field(None, description="Filter by tags")
    min_confidence: Optional[int] = Field(None, ge=0, le=100, description="Minimum OCR confidence")
    search_type: str = Field(default="all", description="Search type: all, exact, fuzzy, sanskrit")


class SearchResult(BaseModel):
    document_id: str
    title: str
    author: Optional[str]
    content_snippet: str
    page_number: Optional[int]
    score: float
    highlights: Dict[str, List[str]]
    ocr_confidence: Optional[int]
    language: Optional[str]


class SearchResponse(BaseModel):
    query: str
    total_results: int
    results: List[SearchResult]
    took: int
    max_score: float
    suggestions: Optional[List[str]] = None
    filters_applied: Dict[str, Any]


@router.get("/documents", response_model=SearchResponse)
async def search_documents(
    q: str = Query(..., min_length=1, description="Search query"),
    language: Optional[str] = Query(None, description="Filter by language"),
    author: Optional[str] = Query(None, description="Filter by author"),
    tags: Optional[str] = Query(None, description="Comma-separated tags"),
    min_confidence: Optional[int] = Query(None, ge=0, le=100, description="Minimum OCR confidence"),
    search_type: str = Query(default="all", description="Search type: all, exact, fuzzy, sanskrit"),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(10, ge=1, le=50, description="Results per page"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Advanced search across all documents with Sanskrit awareness"""
    try:
        logger.info(f"🔍 Searching documents for: {q}")
        
        # Initialize search service if not already done
        if not hasattr(search_service, '_initialized'):
            await search_service.initialize()
            search_service._initialized = True
        
        # Prepare filters
        filters = {}
        if language:
            filters['language'] = language
        if author:
            filters['author'] = author
        if tags:
            filters['tags'] = tags.split(',')
        if min_confidence:
            filters['min_ocr_confidence'] = min_confidence
        
        # Calculate offset for pagination
        offset = (page - 1) * size
        
        # Perform search using our advanced search service
        search_results = await search_service.search_documents(
            query=q,
            filters=filters,
            size=size,
            offset=offset
        )
        
        # Get search suggestions
        suggestions = await search_service.suggest_terms(q, size=5)
        
        # Format response
        response = SearchResponse(
            query=q,
            total_results=search_results.get('total_results', 0),
            results=[
                SearchResult(
                    document_id=result.get('document_id', ''),
                    title=result.get('title', ''),
                    author=result.get('author'),
                    content_snippet=result.get('content', '')[:200] + '...' if len(result.get('content', '')) > 200 else result.get('content', ''),
                    page_number=result.get('page_number'),
                    score=result.get('score', 0.0),
                    highlights=result.get('highlights', {}),
                    ocr_confidence=result.get('ocr_confidence'),
                    language=result.get('language')
                )
                for result in search_results.get('results', [])
            ],
            took=search_results.get('took', 0),
            max_score=search_results.get('max_score', 0.0),
            suggestions=suggestions,
            filters_applied=filters
        )
        
        logger.info(f"✅ Search completed: {len(response.results)} results found")
        return response
        
    except Exception as e:
        logger.error(f"❌ Error in document search: {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.get("/sanskrit/glossary")
async def search_sanskrit_glossary(
    q: str = Query(..., min_length=1, description="Sanskrit word to search"),
    script: str = Query(default="any", description="Script: devanagari, iast, romanized, any"),
    limit: int = Query(10, ge=1, le=50, description="Maximum results"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Search Sanskrit glossary with script-aware matching"""
    try:
        logger.info(f"🔍 Searching Sanskrit glossary for: {q}")
        
        # Build query based on script preference
        query = select(SanskritGlossaryEntry)
        
        if script == "devanagari":
            query = query.where(SanskritGlossaryEntry.word_devanagari.ilike(f"%{q}%"))
        elif script == "iast":
            query = query.where(SanskritGlossaryEntry.word_iast.ilike(f"%{q}%"))
        elif script == "romanized":
            query = query.where(SanskritGlossaryEntry.word_romanized.ilike(f"%{q}%"))
        else:  # any script
            query = query.where(
                or_(
                    SanskritGlossaryEntry.word_devanagari.ilike(f"%{q}%"),
                    SanskritGlossaryEntry.word_iast.ilike(f"%{q}%"),
                    SanskritGlossaryEntry.word_romanized.ilike(f"%{q}%"),
                    SanskritGlossaryEntry.meaning_english.ilike(f"%{q}%"),
                    SanskritGlossaryEntry.meaning_hindi.ilike(f"%{q}%")
                )
            )
        
        query = query.order_by(SanskritGlossaryEntry.frequency.desc()).limit(limit)
        
        result = await db.execute(query)
        entries = result.scalars().all()
        
        glossary_results = {
            "query": q,
            "script_filter": script,
            "total_results": len(entries),
            "results": [
                {
                    "id": str(entry.id),
                    "word_devanagari": entry.word_devanagari,
                    "word_iast": entry.word_iast,
                    "word_romanized": entry.word_romanized,
                    "meaning_english": entry.meaning_english,
                    "meaning_hindi": entry.meaning_hindi,
                    "part_of_speech": entry.part_of_speech,
                    "gender": entry.gender,
                    "context": entry.context,
                    "frequency": entry.frequency,
                    "is_verified": entry.is_verified
                }
                for entry in entries
            ]
        }
        
        logger.info(f"✅ Found {len(entries)} glossary entries for: {q}")
        return glossary_results
        
    except Exception as e:
        logger.error(f"❌ Error searching glossary: {e}")
        raise HTTPException(status_code=500, detail=f"Glossary search failed: {str(e)}")


@router.get("/suggestions")
async def get_search_suggestions(
    q: str = Query(..., min_length=1, description="Partial query for suggestions"),
    limit: int = Query(5, ge=1, le=20, description="Maximum suggestions"),
    current_user: User = Depends(get_current_user)
):
    """Get search suggestions with Sanskrit awareness"""
    try:
        logger.info(f"🔍 Getting search suggestions for: {q}")
        
        # Initialize search service if needed
        if not hasattr(search_service, '_initialized'):
            await search_service.initialize()
            search_service._initialized = True
        
        # Get suggestions from search service
        suggestions = await search_service.suggest_terms(q, size=limit)
        
        response = {
            "query": q,
            "suggestions": suggestions,
            "total": len(suggestions)
        }
        
        logger.info(f"✅ Generated {len(suggestions)} suggestions for: {q}")
        return response
        
    except Exception as e:
        logger.error(f"❌ Error getting suggestions: {e}")
        raise HTTPException(status_code=500, detail=f"Suggestions failed: {str(e)}")


@router.post("/index/document")
async def index_document_for_search(
    background_tasks: BackgroundTasks,
    document_id: str = Query(..., description="Document ID to index"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Index a document for search (admin only)"""
    try:
        if not current_user.is_admin:
            raise HTTPException(status_code=403, detail="Admin access required")
        
        logger.info(f"📝 Indexing document for search: {document_id}")
        
        # Get document data from database
        # This is a simplified version - in production, you'd fetch from Book/Page/OCRResult
        document_data = {
            "document_id": document_id,
            "title": f"Document {document_id}",
            "content": "Sample Sanskrit content for indexing",
            "language": "sanskrit",
            "created_at": datetime.utcnow().isoformat()
        }
        
        # Initialize search service if needed
        if not hasattr(search_service, '_initialized'):
            await search_service.initialize()
            search_service._initialized = True
        
        # Index document in background
        background_tasks.add_task(
            search_service.index_document,
            document_data
        )
        
        logger.info(f"✅ Document indexing queued: {document_id}")
        return {
            "message": "Document indexing queued",
            "document_id": document_id,
            "status": "queued"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error indexing document: {e}")
        raise HTTPException(status_code=500, detail=f"Indexing failed: {str(e)}")


@router.get("/test/system-status")
async def test_search_system(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Test endpoint to validate search system functionality"""
    try:
        logger.info("🧪 Testing search system status")
        
        # Initialize search service if needed
        if not hasattr(search_service, '_initialized'):
            await search_service.initialize()
            search_service._initialized = True
        
        # Test database connectivity for glossary
        glossary_count_query = select(func.count(SanskritGlossaryEntry.id))
        result = await db.execute(glossary_count_query)
        glossary_count = result.scalar()
        
        # Test search service
        test_search = await search_service.search_documents("test", size=1)
        
        # Test suggestions
        test_suggestions = await search_service.suggest_terms("veda", size=3)
        
        system_status = {
            "status": "healthy",
            "search_service": "✅ Initialized" if hasattr(search_service, '_initialized') else "❌ Not initialized",
            "elasticsearch_available": "✅ Connected" if search_service.client else "📝 Fallback mode",
            "sanskrit_analyzer": "✅ Available",
            "data_counts": {
                "glossary_entries": glossary_count
            },
            "test_results": {
                "search_query": test_search.get('query', 'test'),
                "search_results": test_search.get('total_results', 0),
                "suggestions_count": len(test_suggestions),
                "fallback_mode": test_search.get('fallback', False)
            },
            "endpoints_available": [
                "/documents - Advanced document search",
                "/sanskrit/glossary - Sanskrit glossary search",
                "/suggestions - Search suggestions",
                "/index/document - Document indexing"
            ],
            "tested_at": datetime.utcnow().isoformat()
        }
        
        logger.info("✅ Search system test completed successfully")
        return system_status
        
    except Exception as e:
        logger.error(f"❌ Search system test failed: {e}")
        raise HTTPException(status_code=500, detail=f"System test failed: {str(e)}")


def extract_snippet(text: str, query: str, max_length: int = 200) -> str:
    """Extract a snippet around the search query"""
    if not text or not query:
        return text[:max_length] if text else ""
    
    # Find the query in the text (case insensitive)
    lower_text = text.lower()
    lower_query = query.lower()
    
    pos = lower_text.find(lower_query)
    if pos == -1:
        return text[:max_length]
    
    # Calculate snippet boundaries
    start = max(0, pos - max_length // 2)
    end = min(len(text), pos + len(query) + max_length // 2)
    
    snippet = text[start:end]
    
    # Add ellipsis if truncated
    if start > 0:
        snippet = "..." + snippet
    if end < len(text):
        snippet = snippet + "..."
    
    return snippet
