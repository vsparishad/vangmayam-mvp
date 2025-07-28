"""
Glossary API endpoints for Sanskrit dictionary
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from typing import List, Optional
import uuid

from app.core.database import get_db
from app.models.glossary import GlossaryEntry
from app.models.user import User
from app.api.deps import get_current_user, get_optional_user

router = APIRouter()


@router.get("/")
async def search_glossary(
    q: str = Query(..., min_length=1),
    language: str = Query("sanskrit"),
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_optional_user)
):
    """Search glossary entries"""
    query = select(GlossaryEntry).where(
        GlossaryEntry.language == language,
        or_(
            GlossaryEntry.word.ilike(f"%{q}%"),
            GlossaryEntry.definition.ilike(f"%{q}%")
        )
    ).limit(limit)
    
    result = await db.execute(query)
    entries = result.scalars().all()
    
    return [
        {
            "id": entry.id,
            "word": entry.word,
            "definition": entry.definition,
            "etymology": entry.etymology,
            "pronunciation": entry.pronunciation,
            "language": entry.language,
            "source": entry.source,
            "is_verified": entry.is_verified
        }
        for entry in entries
    ]


@router.post("/")
async def create_glossary_entry(
    word: str,
    definition: str,
    etymology: str = None,
    pronunciation: str = None,
    language: str = "sanskrit",
    source: str = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new glossary entry"""
    entry = GlossaryEntry(
        word=word,
        definition=definition,
        etymology=etymology,
        pronunciation=pronunciation,
        language=language,
        source=source,
        created_by=current_user.id,
        is_verified=current_user.is_editor
    )
    
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    
    return {
        "id": entry.id,
        "word": entry.word,
        "definition": entry.definition,
        "etymology": entry.etymology,
        "pronunciation": entry.pronunciation,
        "language": entry.language,
        "source": entry.source,
        "is_verified": entry.is_verified
    }
