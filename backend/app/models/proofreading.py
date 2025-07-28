"""
Proofreading and Editorial Workflow Models for Vāṇmayam

This module defines database models for:
- Proofreading sessions and tasks
- OCR text corrections and edits
- Collaborative editing with user tracking
- Version control and approval workflow
- Sanskrit text validation and glossary integration
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, JSON, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid
import enum

from ..core.database import Base


class ProofreadingStatus(str, enum.Enum):
    """Status enum for proofreading tasks"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    COMPLETED = "completed"


class EditType(str, enum.Enum):
    """Type of edit made during proofreading"""
    CORRECTION = "correction"
    ADDITION = "addition"
    DELETION = "deletion"
    FORMATTING = "formatting"
    TRANSLITERATION = "transliteration"
    ANNOTATION = "annotation"


class ProofreadingTask(Base):
    """
    Main proofreading task model
    Represents a document or page that needs proofreading
    """
    __tablename__ = "proofreading_tasks"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Source information
    source_document_id = Column(String, nullable=False, index=True)
    source_page_number = Column(Integer, nullable=True)
    source_image_path = Column(String, nullable=True)
    
    # OCR data
    original_ocr_text = Column(Text, nullable=False)
    ocr_confidence = Column(Integer, default=0)  # 0-100
    alto_xml_path = Column(String, nullable=True)
    
    # Current state
    current_text = Column(Text, nullable=False)
    status = Column(Enum(ProofreadingStatus), default=ProofreadingStatus.PENDING, index=True)
    
    # Assignment and tracking
    assigned_to = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    reviewer_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    
    # Metadata
    language = Column(String, default="sanskrit")
    difficulty_level = Column(Integer, default=1)  # 1-5 scale
    estimated_time_minutes = Column(Integer, nullable=True)
    actual_time_minutes = Column(Integer, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    assigned_at = Column(DateTime, nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    approved_at = Column(DateTime, nullable=True)
    
    # Quality metrics
    edit_count = Column(Integer, default=0)
    character_accuracy = Column(Integer, nullable=True)  # Percentage
    word_accuracy = Column(Integer, nullable=True)  # Percentage
    
    # Relationships
    edits = relationship("ProofreadingEdit", back_populates="task", cascade="all, delete-orphan")
    comments = relationship("ProofreadingComment", back_populates="task", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<ProofreadingTask {self.id}: {self.status}>"


class ProofreadingEdit(Base):
    """
    Individual edit made during proofreading
    Tracks all changes with full history
    """
    __tablename__ = "proofreading_edits"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id = Column(UUID(as_uuid=True), ForeignKey("proofreading_tasks.id"), nullable=False)
    
    # Edit details
    edit_type = Column(Enum(EditType), nullable=False)
    
    # Text positions (character-based)
    start_position = Column(Integer, nullable=False)
    end_position = Column(Integer, nullable=False)
    
    # Content
    original_text = Column(Text, nullable=False)
    corrected_text = Column(Text, nullable=False)
    
    # Context
    context_before = Column(String(100), nullable=True)
    context_after = Column(String(100), nullable=True)
    
    # Metadata
    confidence = Column(Integer, default=100)  # Editor's confidence in the edit
    reason = Column(String, nullable=True)  # Reason for the edit
    sanskrit_rule = Column(String, nullable=True)  # Sanskrit grammar rule if applicable
    
    # User and timing
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Approval status
    is_approved = Column(Boolean, default=None, nullable=True)
    approved_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    
    # Relationships
    task = relationship("ProofreadingTask", back_populates="edits")
    user = relationship("User", foreign_keys=[user_id])
    approver = relationship("User", foreign_keys=[approved_by])
    
    def __repr__(self):
        return f"<ProofreadingEdit {self.id}: {self.edit_type}>"


class ProofreadingComment(Base):
    """
    Comments and annotations on proofreading tasks
    Supports collaborative discussion
    """
    __tablename__ = "proofreading_comments"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id = Column(UUID(as_uuid=True), ForeignKey("proofreading_tasks.id"), nullable=False)
    
    # Comment content
    content = Column(Text, nullable=False)
    comment_type = Column(String, default="general")  # general, question, suggestion, etc.
    
    # Position reference (optional)
    text_position = Column(Integer, nullable=True)
    text_selection = Column(String, nullable=True)
    
    # User and timing
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Threading
    parent_comment_id = Column(UUID(as_uuid=True), ForeignKey("proofreading_comments.id"), nullable=True)
    
    # Status
    is_resolved = Column(Boolean, default=False)
    resolved_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    
    # Relationships
    task = relationship("ProofreadingTask", back_populates="comments")
    user = relationship("User", foreign_keys=[user_id])
    resolver = relationship("User", foreign_keys=[resolved_by])
    parent_comment = relationship("ProofreadingComment", remote_side=[id])
    replies = relationship("ProofreadingComment", back_populates="parent_comment")
    
    def __repr__(self):
        return f"<ProofreadingComment {self.id}: {self.comment_type}>"


class ProofreadingSession(Base):
    """
    User session for proofreading work
    Tracks active editing sessions and collaboration
    """
    __tablename__ = "proofreading_sessions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Session details
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    task_id = Column(UUID(as_uuid=True), ForeignKey("proofreading_tasks.id"), nullable=False)
    
    # Session state
    is_active = Column(Boolean, default=True)
    cursor_position = Column(Integer, default=0)
    selected_text_start = Column(Integer, nullable=True)
    selected_text_end = Column(Integer, nullable=True)
    
    # Timing
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_activity = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    ended_at = Column(DateTime, nullable=True)
    
    # Metrics
    characters_edited = Column(Integer, default=0)
    edits_made = Column(Integer, default=0)
    time_spent_seconds = Column(Integer, default=0)
    
    # Relationships
    user = relationship("User")
    task = relationship("ProofreadingTask")
    
    def __repr__(self):
        return f"<ProofreadingSession {self.id}: {self.user_id}>"


class SanskritGlossaryEntry(Base):
    """
    Sanskrit glossary for proofreading assistance
    Helps with word recognition and validation
    """
    __tablename__ = "sanskrit_glossary"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Word information
    word_devanagari = Column(String, nullable=False, index=True)
    word_iast = Column(String, nullable=False, index=True)  # International Alphabet of Sanskrit Transliteration
    word_romanized = Column(String, nullable=True, index=True)
    
    # Linguistic details
    part_of_speech = Column(String, nullable=True)
    gender = Column(String, nullable=True)  # masculine, feminine, neuter
    case = Column(String, nullable=True)  # nominative, accusative, etc.
    number = Column(String, nullable=True)  # singular, dual, plural
    
    # Meaning and context
    meaning_english = Column(Text, nullable=True)
    meaning_hindi = Column(Text, nullable=True)
    context = Column(String, nullable=True)  # vedic, classical, modern
    
    # Usage statistics
    frequency = Column(Integer, default=1)
    last_used = Column(DateTime, default=datetime.utcnow)
    
    # Source and validation
    source = Column(String, nullable=True)  # dictionary, text, user
    is_verified = Column(Boolean, default=False)
    verified_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    verifier = relationship("User")
    
    def __repr__(self):
        return f"<SanskritGlossaryEntry {self.word_devanagari}: {self.word_iast}>"


class ProofreadingQualityMetrics(Base):
    """
    Quality metrics and analytics for proofreading work
    Tracks accuracy, speed, and improvement over time
    """
    __tablename__ = "proofreading_quality_metrics"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Reference
    task_id = Column(UUID(as_uuid=True), ForeignKey("proofreading_tasks.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    # Accuracy metrics
    character_accuracy = Column(Integer, nullable=True)  # Percentage
    word_accuracy = Column(Integer, nullable=True)  # Percentage
    line_accuracy = Column(Integer, nullable=True)  # Percentage
    
    # Speed metrics
    characters_per_minute = Column(Integer, nullable=True)
    words_per_minute = Column(Integer, nullable=True)
    
    # Error analysis
    total_errors_found = Column(Integer, default=0)
    ocr_errors_corrected = Column(Integer, default=0)
    false_corrections = Column(Integer, default=0)
    
    # Sanskrit-specific metrics
    sanskrit_words_corrected = Column(Integer, default=0)
    transliteration_accuracy = Column(Integer, nullable=True)
    grammar_corrections = Column(Integer, default=0)
    
    # Calculated at task completion
    calculated_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    task = relationship("ProofreadingTask")
    user = relationship("User")
    
    def __repr__(self):
        return f"<ProofreadingQualityMetrics {self.task_id}: {self.character_accuracy}%>"
