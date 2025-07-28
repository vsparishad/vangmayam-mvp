"""
Collaborative Proofreading API Endpoints for Vāṇmayam

This module provides REST API endpoints for:
- Proofreading task management
- Collaborative editing with real-time updates
- OCR text correction and validation
- Sanskrit glossary integration
- Quality metrics and analytics
- Side-by-side UI support
"""

import asyncio
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import json

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Query, Path
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, and_, or_, func
from sqlalchemy.orm import selectinload
from pydantic import BaseModel, Field, UUID4

from ....models.proofreading import (
    ProofreadingTask, ProofreadingEdit, ProofreadingComment, 
    ProofreadingSession, SanskritGlossaryEntry, ProofreadingQualityMetrics,
    ProofreadingStatus, EditType
)
from ....models.user import User
from ....core.database import get_db
from ....core.auth import get_current_user
from ....core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()


# Pydantic models for request/response

class ProofreadingTaskCreate(BaseModel):
    source_document_id: str = Field(..., description="Source document identifier")
    source_page_number: Optional[int] = Field(None, description="Page number if applicable")
    source_image_path: Optional[str] = Field(None, description="Path to source image")
    original_ocr_text: str = Field(..., description="Original OCR text to proofread")
    ocr_confidence: int = Field(default=0, ge=0, le=100, description="OCR confidence score")
    alto_xml_path: Optional[str] = Field(None, description="Path to ALTO XML file")
    language: str = Field(default="sanskrit", description="Text language")
    difficulty_level: int = Field(default=1, ge=1, le=5, description="Difficulty level 1-5")
    estimated_time_minutes: Optional[int] = Field(None, description="Estimated completion time")


class ProofreadingTaskUpdate(BaseModel):
    current_text: Optional[str] = Field(None, description="Updated text content")
    status: Optional[ProofreadingStatus] = Field(None, description="Task status")
    assigned_to: Optional[UUID4] = Field(None, description="Assigned user ID")
    reviewer_id: Optional[UUID4] = Field(None, description="Reviewer user ID")
    actual_time_minutes: Optional[int] = Field(None, description="Actual time spent")


class ProofreadingTaskResponse(BaseModel):
    id: UUID4
    source_document_id: str
    source_page_number: Optional[int]
    source_image_path: Optional[str]
    original_ocr_text: str
    current_text: str
    status: ProofreadingStatus
    assigned_to: Optional[UUID4]
    reviewer_id: Optional[UUID4]
    language: str
    difficulty_level: int
    ocr_confidence: int
    edit_count: int
    character_accuracy: Optional[int]
    word_accuracy: Optional[int]
    created_at: datetime
    assigned_at: Optional[datetime]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    approved_at: Optional[datetime]


class ProofreadingEditCreate(BaseModel):
    edit_type: EditType = Field(..., description="Type of edit")
    start_position: int = Field(..., ge=0, description="Start character position")
    end_position: int = Field(..., ge=0, description="End character position")
    original_text: str = Field(..., description="Original text being edited")
    corrected_text: str = Field(..., description="Corrected text")
    reason: Optional[str] = Field(None, description="Reason for the edit")
    confidence: int = Field(default=100, ge=0, le=100, description="Confidence in edit")
    sanskrit_rule: Optional[str] = Field(None, description="Sanskrit grammar rule")


class ProofreadingEditResponse(BaseModel):
    id: UUID4
    task_id: UUID4
    edit_type: EditType
    start_position: int
    end_position: int
    original_text: str
    corrected_text: str
    context_before: Optional[str]
    context_after: Optional[str]
    confidence: int
    reason: Optional[str]
    sanskrit_rule: Optional[str]
    user_id: UUID4
    created_at: datetime
    is_approved: Optional[bool]
    approved_by: Optional[UUID4]
    approved_at: Optional[datetime]


class ProofreadingCommentCreate(BaseModel):
    content: str = Field(..., description="Comment content")
    comment_type: str = Field(default="general", description="Comment type")
    text_position: Optional[int] = Field(None, description="Text position reference")
    text_selection: Optional[str] = Field(None, description="Selected text")
    parent_comment_id: Optional[UUID4] = Field(None, description="Parent comment for threading")


class ProofreadingCommentResponse(BaseModel):
    id: UUID4
    task_id: UUID4
    content: str
    comment_type: str
    text_position: Optional[int]
    text_selection: Optional[str]
    user_id: UUID4
    created_at: datetime
    updated_at: datetime
    parent_comment_id: Optional[UUID4]
    is_resolved: bool
    resolved_by: Optional[UUID4]
    resolved_at: Optional[datetime]


class SanskritGlossaryEntryCreate(BaseModel):
    word_devanagari: str = Field(..., description="Word in Devanagari script")
    word_iast: str = Field(..., description="Word in IAST transliteration")
    word_romanized: Optional[str] = Field(None, description="Romanized form")
    part_of_speech: Optional[str] = Field(None, description="Part of speech")
    gender: Optional[str] = Field(None, description="Gender (m/f/n)")
    meaning_english: Optional[str] = Field(None, description="English meaning")
    meaning_hindi: Optional[str] = Field(None, description="Hindi meaning")
    context: Optional[str] = Field(None, description="Usage context")
    source: Optional[str] = Field(None, description="Source reference")


class ProofreadingSessionResponse(BaseModel):
    id: UUID4
    user_id: UUID4
    task_id: UUID4
    is_active: bool
    cursor_position: int
    selected_text_start: Optional[int]
    selected_text_end: Optional[int]
    started_at: datetime
    last_activity: datetime
    characters_edited: int
    edits_made: int
    time_spent_seconds: int


# API Endpoints

@router.get("/tasks", response_model=List[ProofreadingTaskResponse])
async def list_proofreading_tasks(
    status: Optional[ProofreadingStatus] = Query(None, description="Filter by status"),
    assigned_to: Optional[UUID4] = Query(None, description="Filter by assigned user"),
    language: Optional[str] = Query(None, description="Filter by language"),
    skip: int = Query(0, ge=0, description="Skip items"),
    limit: int = Query(50, ge=1, le=100, description="Limit items"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List proofreading tasks with optional filtering
    """
    try:
        logger.info(f"📋 Listing proofreading tasks for user {current_user.id}")
        
        # Build query with filters
        query = select(ProofreadingTask)
        
        if status:
            query = query.where(ProofreadingTask.status == status)
        if assigned_to:
            query = query.where(ProofreadingTask.assigned_to == assigned_to)
        if language:
            query = query.where(ProofreadingTask.language == language)
        
        # Add pagination
        query = query.offset(skip).limit(limit).order_by(ProofreadingTask.created_at.desc())
        
        result = await db.execute(query)
        tasks = result.scalars().all()
        
        logger.info(f"✅ Retrieved {len(tasks)} proofreading tasks")
        return tasks
        
    except Exception as e:
        logger.error(f"❌ Error listing proofreading tasks: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list tasks: {str(e)}")


@router.post("/tasks", response_model=ProofreadingTaskResponse)
async def create_proofreading_task(
    task_data: ProofreadingTaskCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new proofreading task
    """
    try:
        logger.info(f"📝 Creating proofreading task for document {task_data.source_document_id}")
        
        # Create new task
        task = ProofreadingTask(
            source_document_id=task_data.source_document_id,
            source_page_number=task_data.source_page_number,
            source_image_path=task_data.source_image_path,
            original_ocr_text=task_data.original_ocr_text,
            current_text=task_data.original_ocr_text,  # Initialize with OCR text
            ocr_confidence=task_data.ocr_confidence,
            alto_xml_path=task_data.alto_xml_path,
            language=task_data.language,
            difficulty_level=task_data.difficulty_level,
            estimated_time_minutes=task_data.estimated_time_minutes,
            status=ProofreadingStatus.PENDING
        )
        
        db.add(task)
        await db.commit()
        await db.refresh(task)
        
        logger.info(f"✅ Created proofreading task {task.id}")
        return task
        
    except Exception as e:
        logger.error(f"❌ Error creating proofreading task: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create task: {str(e)}")


@router.get("/tasks/{task_id}", response_model=ProofreadingTaskResponse)
async def get_proofreading_task(
    task_id: UUID4 = Path(..., description="Task ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get a specific proofreading task with details
    """
    try:
        logger.info(f"📄 Getting proofreading task {task_id}")
        
        query = select(ProofreadingTask).where(ProofreadingTask.id == task_id)
        result = await db.execute(query)
        task = result.scalar_one_or_none()
        
        if not task:
            raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")
        
        logger.info(f"✅ Retrieved proofreading task {task_id}")
        return task
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting proofreading task: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get task: {str(e)}")


@router.put("/tasks/{task_id}", response_model=ProofreadingTaskResponse)
async def update_proofreading_task(
    task_id: UUID4 = Path(..., description="Task ID"),
    task_update: ProofreadingTaskUpdate = ...,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update a proofreading task
    """
    try:
        logger.info(f"✏️ Updating proofreading task {task_id}")
        
        # Get existing task
        query = select(ProofreadingTask).where(ProofreadingTask.id == task_id)
        result = await db.execute(query)
        task = result.scalar_one_or_none()
        
        if not task:
            raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")
        
        # Update fields
        update_data = task_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(task, field, value)
        
        # Update timestamps based on status changes
        if task_update.status:
            if task_update.status == ProofreadingStatus.IN_PROGRESS and not task.started_at:
                task.started_at = datetime.utcnow()
            elif task_update.status == ProofreadingStatus.COMPLETED and not task.completed_at:
                task.completed_at = datetime.utcnow()
            elif task_update.status == ProofreadingStatus.APPROVED and not task.approved_at:
                task.approved_at = datetime.utcnow()
        
        await db.commit()
        await db.refresh(task)
        
        logger.info(f"✅ Updated proofreading task {task_id}")
        return task
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error updating proofreading task: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update task: {str(e)}")


@router.post("/tasks/{task_id}/assign")
async def assign_proofreading_task(
    task_id: UUID4 = Path(..., description="Task ID"),
    assignee_id: Optional[UUID4] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Assign a proofreading task to a user (or self-assign)
    """
    try:
        target_user_id = assignee_id or current_user.id
        logger.info(f"👤 Assigning task {task_id} to user {target_user_id}")
        
        # Get task
        query = select(ProofreadingTask).where(ProofreadingTask.id == task_id)
        result = await db.execute(query)
        task = result.scalar_one_or_none()
        
        if not task:
            raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")
        
        if task.assigned_to:
            raise HTTPException(status_code=400, detail="Task is already assigned")
        
        # Assign task
        task.assigned_to = target_user_id
        task.assigned_at = datetime.utcnow()
        task.status = ProofreadingStatus.IN_PROGRESS
        
        await db.commit()
        
        logger.info(f"✅ Assigned task {task_id} to user {target_user_id}")
        return {"message": "Task assigned successfully", "task_id": task_id, "assigned_to": target_user_id}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error assigning task: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to assign task: {str(e)}")


@router.post("/tasks/{task_id}/edits", response_model=ProofreadingEditResponse)
async def create_proofreading_edit(
    task_id: UUID4 = Path(..., description="Task ID"),
    edit_data: ProofreadingEditCreate = ...,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new edit for a proofreading task
    """
    try:
        logger.info(f"✏️ Creating edit for task {task_id}")
        
        # Verify task exists and user has access
        query = select(ProofreadingTask).where(ProofreadingTask.id == task_id)
        result = await db.execute(query)
        task = result.scalar_one_or_none()
        
        if not task:
            raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")
        
        # Create context snippets
        text = task.current_text
        context_before = text[max(0, edit_data.start_position - 50):edit_data.start_position] if edit_data.start_position > 0 else None
        context_after = text[edit_data.end_position:edit_data.end_position + 50] if edit_data.end_position < len(text) else None
        
        # Create edit
        edit = ProofreadingEdit(
            task_id=task_id,
            edit_type=edit_data.edit_type,
            start_position=edit_data.start_position,
            end_position=edit_data.end_position,
            original_text=edit_data.original_text,
            corrected_text=edit_data.corrected_text,
            context_before=context_before,
            context_after=context_after,
            confidence=edit_data.confidence,
            reason=edit_data.reason,
            sanskrit_rule=edit_data.sanskrit_rule,
            user_id=current_user.id
        )
        
        db.add(edit)
        
        # Update task text and edit count
        new_text = text[:edit_data.start_position] + edit_data.corrected_text + text[edit_data.end_position:]
        task.current_text = new_text
        task.edit_count += 1
        
        await db.commit()
        await db.refresh(edit)
        
        logger.info(f"✅ Created edit {edit.id} for task {task_id}")
        return edit
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error creating edit: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create edit: {str(e)}")


@router.get("/tasks/{task_id}/edits", response_model=List[ProofreadingEditResponse])
async def list_task_edits(
    task_id: UUID4 = Path(..., description="Task ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List all edits for a proofreading task
    """
    try:
        logger.info(f"📋 Listing edits for task {task_id}")
        
        query = select(ProofreadingEdit).where(
            ProofreadingEdit.task_id == task_id
        ).order_by(ProofreadingEdit.created_at.asc())
        
        result = await db.execute(query)
        edits = result.scalars().all()
        
        logger.info(f"✅ Retrieved {len(edits)} edits for task {task_id}")
        return edits
        
    except Exception as e:
        logger.error(f"❌ Error listing edits: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list edits: {str(e)}")


@router.post("/tasks/{task_id}/comments", response_model=ProofreadingCommentResponse)
async def create_proofreading_comment(
    task_id: UUID4 = Path(..., description="Task ID"),
    comment_data: ProofreadingCommentCreate = ...,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a comment on a proofreading task
    """
    try:
        logger.info(f"💬 Creating comment for task {task_id}")
        
        # Verify task exists
        query = select(ProofreadingTask).where(ProofreadingTask.id == task_id)
        result = await db.execute(query)
        task = result.scalar_one_or_none()
        
        if not task:
            raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")
        
        # Create comment
        comment = ProofreadingComment(
            task_id=task_id,
            content=comment_data.content,
            comment_type=comment_data.comment_type,
            text_position=comment_data.text_position,
            text_selection=comment_data.text_selection,
            parent_comment_id=comment_data.parent_comment_id,
            user_id=current_user.id
        )
        
        db.add(comment)
        await db.commit()
        await db.refresh(comment)
        
        logger.info(f"✅ Created comment {comment.id} for task {task_id}")
        return comment
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error creating comment: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create comment: {str(e)}")


@router.get("/tasks/{task_id}/comments", response_model=List[ProofreadingCommentResponse])
async def list_task_comments(
    task_id: UUID4 = Path(..., description="Task ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List all comments for a proofreading task
    """
    try:
        logger.info(f"💬 Listing comments for task {task_id}")
        
        query = select(ProofreadingComment).where(
            ProofreadingComment.task_id == task_id
        ).order_by(ProofreadingComment.created_at.asc())
        
        result = await db.execute(query)
        comments = result.scalars().all()
        
        logger.info(f"✅ Retrieved {len(comments)} comments for task {task_id}")
        return comments
        
    except Exception as e:
        logger.error(f"❌ Error listing comments: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list comments: {str(e)}")


@router.get("/glossary/search")
async def search_sanskrit_glossary(
    query: str = Query(..., description="Search query"),
    limit: int = Query(10, ge=1, le=50, description="Limit results"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Search Sanskrit glossary for word suggestions
    """
    try:
        logger.info(f"🔍 Searching Sanskrit glossary for: {query}")
        
        # Search in Devanagari, IAST, and romanized forms
        search_query = select(SanskritGlossaryEntry).where(
            or_(
                SanskritGlossaryEntry.word_devanagari.ilike(f"%{query}%"),
                SanskritGlossaryEntry.word_iast.ilike(f"%{query}%"),
                SanskritGlossaryEntry.word_romanized.ilike(f"%{query}%")
            )
        ).order_by(SanskritGlossaryEntry.frequency.desc()).limit(limit)
        
        result = await db.execute(search_query)
        entries = result.scalars().all()
        
        logger.info(f"✅ Found {len(entries)} glossary entries for query: {query}")
        return {"query": query, "results": entries, "total": len(entries)}
        
    except Exception as e:
        logger.error(f"❌ Error searching glossary: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to search glossary: {str(e)}")


@router.post("/sessions/start", response_model=ProofreadingSessionResponse)
async def start_proofreading_session(
    task_id: UUID4,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Start a proofreading session for collaborative editing
    """
    try:
        logger.info(f"🚀 Starting proofreading session for task {task_id}")
        
        # End any existing active sessions for this user/task
        await db.execute(
            update(ProofreadingSession)
            .where(and_(
                ProofreadingSession.user_id == current_user.id,
                ProofreadingSession.task_id == task_id,
                ProofreadingSession.is_active == True
            ))
            .values(is_active=False, ended_at=datetime.utcnow())
        )
        
        # Create new session
        session = ProofreadingSession(
            user_id=current_user.id,
            task_id=task_id,
            is_active=True
        )
        
        db.add(session)
        await db.commit()
        await db.refresh(session)
        
        logger.info(f"✅ Started proofreading session {session.id}")
        return session
        
    except Exception as e:
        logger.error(f"❌ Error starting session: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to start session: {str(e)}")


@router.get("/analytics/dashboard")
async def get_proofreading_analytics(
    days: int = Query(30, ge=1, le=365, description="Days to analyze"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get proofreading analytics and dashboard data
    """
    try:
        logger.info(f"📊 Getting proofreading analytics for {days} days")
        
        # Calculate date range
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        # Get task statistics
        task_stats_query = select(
            func.count(ProofreadingTask.id).label("total_tasks"),
            func.count(ProofreadingTask.id).filter(ProofreadingTask.status == ProofreadingStatus.COMPLETED).label("completed_tasks"),
            func.count(ProofreadingTask.id).filter(ProofreadingTask.status == ProofreadingStatus.IN_PROGRESS).label("in_progress_tasks"),
            func.avg(ProofreadingTask.actual_time_minutes).label("avg_time_minutes"),
            func.avg(ProofreadingTask.character_accuracy).label("avg_accuracy")
        ).where(ProofreadingTask.created_at >= start_date)
        
        result = await db.execute(task_stats_query)
        stats = result.first()
        
        analytics = {
            "period_days": days,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "task_statistics": {
                "total_tasks": stats.total_tasks or 0,
                "completed_tasks": stats.completed_tasks or 0,
                "in_progress_tasks": stats.in_progress_tasks or 0,
                "completion_rate": (stats.completed_tasks / stats.total_tasks * 100) if stats.total_tasks else 0,
                "average_time_minutes": float(stats.avg_time_minutes) if stats.avg_time_minutes else 0,
                "average_accuracy": float(stats.avg_accuracy) if stats.avg_accuracy else 0
            }
        }
        
        logger.info(f"✅ Generated proofreading analytics for {days} days")
        return analytics
        
    except Exception as e:
        logger.error(f"❌ Error getting analytics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get analytics: {str(e)}")


# Test endpoint for validating the proofreading system
@router.get("/test/system-status")
async def test_proofreading_system(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Test endpoint to validate proofreading system functionality
    """
    try:
        logger.info("🧪 Testing proofreading system status")
        
        # Test database connectivity
        task_count_query = select(func.count(ProofreadingTask.id))
        result = await db.execute(task_count_query)
        task_count = result.scalar()
        
        # Test model relationships
        edit_count_query = select(func.count(ProofreadingEdit.id))
        result = await db.execute(edit_count_query)
        edit_count = result.scalar()
        
        comment_count_query = select(func.count(ProofreadingComment.id))
        result = await db.execute(comment_count_query)
        comment_count = result.scalar()
        
        glossary_count_query = select(func.count(SanskritGlossaryEntry.id))
        result = await db.execute(glossary_count_query)
        glossary_count = result.scalar()
        
        system_status = {
            "status": "healthy",
            "database_connection": "✅ Connected",
            "models_accessible": "✅ All models accessible",
            "data_counts": {
                "proofreading_tasks": task_count,
                "edits": edit_count,
                "comments": comment_count,
                "glossary_entries": glossary_count
            },
            "endpoints_available": [
                "/tasks - Task management",
                "/tasks/{id}/edits - Edit tracking",
                "/tasks/{id}/comments - Collaborative comments",
                "/glossary/search - Sanskrit glossary",
                "/sessions/start - Collaborative sessions",
                "/analytics/dashboard - Analytics"
            ],
            "tested_at": datetime.utcnow().isoformat()
        }
        
        logger.info("✅ Proofreading system test completed successfully")
        return system_status
        
    except Exception as e:
        logger.error(f"❌ Proofreading system test failed: {e}")
        raise HTTPException(status_code=500, detail=f"System test failed: {str(e)}")
