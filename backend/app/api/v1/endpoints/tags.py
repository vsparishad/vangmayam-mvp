"""
Tags API endpoints for content categorization
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
import uuid

from app.core.database import get_db
from app.models.tag import Tag
from app.models.user import User
from app.api.deps import get_current_user, get_editor_user, get_optional_user

router = APIRouter()


@router.get("/")
async def list_tags(
    approved_only: bool = True,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_optional_user)
):
    """List all tags"""
    query = select(Tag)
    if approved_only:
        query = query.where(Tag.is_approved == True)
    
    result = await db.execute(query.order_by(Tag.name))
    tags = result.scalars().all()
    
    return [
        {
            "id": tag.id,
            "name": tag.name,
            "description": tag.description,
            "category": tag.category,
            "is_approved": tag.is_approved,
            "usage_count": tag.usage_count
        }
        for tag in tags
    ]


@router.post("/")
async def create_tag(
    name: str,
    description: str = None,
    category: str = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new tag"""
    tag = Tag(
        name=name,
        description=description,
        category=category,
        created_by=current_user.id,
        is_approved=current_user.is_editor  # Auto-approve for editors
    )
    
    db.add(tag)
    await db.commit()
    await db.refresh(tag)
    
    return {
        "id": tag.id,
        "name": tag.name,
        "description": tag.description,
        "category": tag.category,
        "is_approved": tag.is_approved
    }
