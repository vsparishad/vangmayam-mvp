"""
Administrator API Endpoints for Vāṇmayam

This module provides REST API endpoints for:
- StarDict dictionary import and management
- Bulk glossary operations
- System administration tasks
- Dictionary validation and statistics
"""

import asyncio
import logging
import os
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, BackgroundTasks, Query
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, func
from pydantic import BaseModel, Field

from ....services.stardict_service import stardict_service
from ....models.proofreading import SanskritGlossaryEntry
from ....core.database import get_db
from ....core.auth import get_current_user, get_current_superuser
from ....models.user import User

logger = logging.getLogger(__name__)

router = APIRouter()


# Pydantic models for request/response

class StarDictImportRequest(BaseModel):
    dict_path: str = Field(..., description="Path to StarDict dictionary files")
    language: str = Field(default="sanskrit", description="Dictionary language")
    context: str = Field(default="imported", description="Import context/category")
    batch_size: int = Field(default=100, ge=1, le=1000, description="Import batch size")
    validate_entries: bool = Field(default=True, description="Validate entries before import")
    deduplicate: bool = Field(default=True, description="Remove duplicate entries")


class StarDictImportResponse(BaseModel):
    dictionary_name: str
    source_path: str
    total_entries: int
    processed_entries: int
    imported_entries: int
    skipped_entries: int
    failed_entries: int
    language: str
    context: str
    import_time: str
    dictionary_info: Dict[str, Any]


class DictionaryInfo(BaseModel):
    source: str
    context: str
    entry_count: int
    first_import: Optional[str]
    last_import: Optional[str]


class GlossaryStats(BaseModel):
    total_entries: int
    verified_entries: int
    unverified_entries: int
    languages: Dict[str, int]
    contexts: Dict[str, int]
    sources: Dict[str, int]
    recent_imports: List[DictionaryInfo]


@router.post("/stardict/import", response_model=StarDictImportResponse)
async def import_stardict_dictionary(
    import_request: StarDictImportRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_superuser)
):
    """
    Import StarDict dictionary files into Sanskrit glossary (Admin only)
    """
    try:
        logger.info(f"📚 Admin {current_user.email} importing StarDict from: {import_request.dict_path}")
        
        # Validate dictionary path exists
        dict_path = Path(import_request.dict_path)
        if not dict_path.exists():
            raise HTTPException(status_code=404, detail=f"Dictionary path not found: {import_request.dict_path}")
        
        # Start import process
        import_result = await stardict_service.import_stardict_dictionary(
            dict_path=import_request.dict_path,
            db=db,
            language=import_request.language,
            context=import_request.context,
            batch_size=import_request.batch_size,
            validate_entries=import_request.validate_entries,
            deduplicate=import_request.deduplicate
        )
        
        logger.info(f"✅ StarDict import completed: {import_result['imported_entries']} entries")
        
        return StarDictImportResponse(**import_result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ StarDict import failed: {e}")
        raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}")


@router.post("/stardict/upload-import")
async def upload_and_import_stardict(
    background_tasks: BackgroundTasks,
    ifo_file: UploadFile = File(..., description="StarDict .ifo file"),
    idx_file: UploadFile = File(..., description="StarDict .idx file"),
    dict_file: UploadFile = File(..., description="StarDict .dict file"),
    language: str = Query(default="sanskrit", description="Dictionary language"),
    context: str = Query(default="uploaded", description="Import context"),
    validate_entries: bool = Query(default=True, description="Validate entries"),
    deduplicate: bool = Query(default=True, description="Remove duplicates"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_superuser)
):
    """
    Upload and import StarDict dictionary files (Admin only)
    """
    try:
        logger.info(f"📤 Admin {current_user.email} uploading StarDict files")
        
        # Validate file extensions
        if not ifo_file.filename.endswith('.ifo'):
            raise HTTPException(status_code=400, detail="Invalid .ifo file")
        if not idx_file.filename.endswith(('.idx', '.idx.gz')):
            raise HTTPException(status_code=400, detail="Invalid .idx file")
        if not dict_file.filename.endswith(('.dict', '.dict.gz')):
            raise HTTPException(status_code=400, detail="Invalid .dict file")
        
        # Create temporary directory for upload
        upload_dir = Path("/tmp/stardict_uploads") / f"upload_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            # Save uploaded files
            base_name = Path(ifo_file.filename).stem
            
            ifo_path = upload_dir / f"{base_name}.ifo"
            idx_path = upload_dir / idx_file.filename
            dict_path = upload_dir / dict_file.filename
            
            # Write files
            with open(ifo_path, 'wb') as f:
                f.write(await ifo_file.read())
            with open(idx_path, 'wb') as f:
                f.write(await idx_file.read())
            with open(dict_path, 'wb') as f:
                f.write(await dict_file.read())
            
            logger.info(f"📁 Files uploaded to: {upload_dir}")
            
            # Import dictionary
            import_result = await stardict_service.import_stardict_dictionary(
                dict_path=str(upload_dir / base_name),
                db=db,
                language=language,
                context=context,
                validate_entries=validate_entries,
                deduplicate=deduplicate
            )
            
            # Clean up uploaded files in background
            background_tasks.add_task(self._cleanup_upload_dir, upload_dir)
            
            logger.info(f"✅ StarDict upload import completed: {import_result['imported_entries']} entries")
            
            return {
                "message": "StarDict dictionary imported successfully",
                "import_result": import_result,
                "uploaded_files": [ifo_file.filename, idx_file.filename, dict_file.filename]
            }
            
        except Exception as e:
            # Clean up on error
            background_tasks.add_task(self._cleanup_upload_dir, upload_dir)
            raise
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ StarDict upload import failed: {e}")
        raise HTTPException(status_code=500, detail=f"Upload import failed: {str(e)}")


@router.get("/dictionaries", response_model=List[DictionaryInfo])
async def list_imported_dictionaries(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_superuser)
):
    """
    List all imported dictionaries with statistics (Admin only)
    """
    try:
        logger.info(f"📊 Admin {current_user.email} listing imported dictionaries")
        
        dictionaries = await stardict_service.list_imported_dictionaries(db)
        
        logger.info(f"✅ Retrieved {len(dictionaries)} dictionary entries")
        return [DictionaryInfo(**d) for d in dictionaries]
        
    except Exception as e:
        logger.error(f"❌ Error listing dictionaries: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list dictionaries: {str(e)}")


@router.get("/glossary/stats", response_model=GlossaryStats)
async def get_glossary_statistics(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_superuser)
):
    """
    Get comprehensive glossary statistics (Admin only)
    """
    try:
        logger.info(f"📈 Admin {current_user.email} requesting glossary statistics")
        
        # Total entries
        total_query = select(func.count(SanskritGlossaryEntry.id))
        total_result = await db.execute(total_query)
        total_entries = total_result.scalar()
        
        # Verified vs unverified
        verified_query = select(func.count(SanskritGlossaryEntry.id)).where(
            SanskritGlossaryEntry.is_verified == True
        )
        verified_result = await db.execute(verified_query)
        verified_entries = verified_result.scalar()
        unverified_entries = total_entries - verified_entries
        
        # Language distribution (using context as proxy)
        lang_query = select(
            SanskritGlossaryEntry.context,
            func.count(SanskritGlossaryEntry.id).label('count')
        ).group_by(SanskritGlossaryEntry.context)
        lang_result = await db.execute(lang_query)
        languages = {row.context or 'unknown': row.count for row in lang_result.fetchall()}
        
        # Context distribution
        context_query = select(
            SanskritGlossaryEntry.context,
            func.count(SanskritGlossaryEntry.id).label('count')
        ).group_by(SanskritGlossaryEntry.context)
        context_result = await db.execute(context_query)
        contexts = {row.context or 'unknown': row.count for row in context_result.fetchall()}
        
        # Source distribution
        source_query = select(
            SanskritGlossaryEntry.source,
            func.count(SanskritGlossaryEntry.id).label('count')
        ).group_by(SanskritGlossaryEntry.source)
        source_result = await db.execute(source_query)
        sources = {row.source or 'unknown': row.count for row in source_result.fetchall()}
        
        # Recent imports
        recent_dictionaries = await stardict_service.list_imported_dictionaries(db)
        recent_imports = sorted(recent_dictionaries, key=lambda x: x.get('last_import', ''), reverse=True)[:5]
        
        stats = GlossaryStats(
            total_entries=total_entries,
            verified_entries=verified_entries,
            unverified_entries=unverified_entries,
            languages=languages,
            contexts=contexts,
            sources=sources,
            recent_imports=[DictionaryInfo(**d) for d in recent_imports]
        )
        
        logger.info(f"✅ Generated glossary statistics: {total_entries} total entries")
        return stats
        
    except Exception as e:
        logger.error(f"❌ Error getting glossary statistics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get statistics: {str(e)}")


@router.delete("/glossary/source/{source_name}")
async def delete_glossary_by_source(
    source_name: str,
    confirm: bool = Query(False, description="Confirm deletion"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_superuser)
):
    """
    Delete all glossary entries from a specific source (Admin only)
    """
    try:
        logger.info(f"🗑️ Admin {current_user.email} deleting glossary source: {source_name}")
        
        if not confirm:
            # Return count for confirmation
            count_query = select(func.count(SanskritGlossaryEntry.id)).where(
                SanskritGlossaryEntry.source == source_name
            )
            count_result = await db.execute(count_query)
            entry_count = count_result.scalar()
            
            return {
                "message": f"Found {entry_count} entries from source '{source_name}'",
                "source": source_name,
                "entry_count": entry_count,
                "confirmation_required": True,
                "note": "Add ?confirm=true to proceed with deletion"
            }
        
        # Perform deletion
        delete_query = delete(SanskritGlossaryEntry).where(
            SanskritGlossaryEntry.source == source_name
        )
        result = await db.execute(delete_query)
        deleted_count = result.rowcount
        
        await db.commit()
        
        logger.info(f"✅ Deleted {deleted_count} entries from source: {source_name}")
        
        return {
            "message": f"Successfully deleted {deleted_count} entries",
            "source": source_name,
            "deleted_count": deleted_count
        }
        
    except Exception as e:
        await db.rollback()
        logger.error(f"❌ Error deleting glossary source: {e}")
        raise HTTPException(status_code=500, detail=f"Deletion failed: {str(e)}")


@router.post("/glossary/verify-entries")
async def bulk_verify_entries(
    source_name: Optional[str] = Query(None, description="Verify entries from specific source"),
    context: Optional[str] = Query(None, description="Verify entries from specific context"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum entries to verify"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_superuser)
):
    """
    Bulk verify glossary entries (Admin only)
    """
    try:
        logger.info(f"✅ Admin {current_user.email} bulk verifying entries")
        
        # Build query
        query = select(SanskritGlossaryEntry).where(
            SanskritGlossaryEntry.is_verified == False
        )
        
        if source_name:
            query = query.where(SanskritGlossaryEntry.source == source_name)
        if context:
            query = query.where(SanskritGlossaryEntry.context == context)
        
        query = query.limit(limit)
        
        # Get entries to verify
        result = await db.execute(query)
        entries = result.scalars().all()
        
        # Update verification status
        verified_count = 0
        for entry in entries:
            entry.is_verified = True
            # Note: verified_by field may need to be added to model
            verified_count += 1
        
        await db.commit()
        
        logger.info(f"✅ Verified {verified_count} glossary entries")
        
        return {
            "message": f"Successfully verified {verified_count} entries",
            "verified_count": verified_count,
            "source_filter": source_name,
            "context_filter": context,
            "verified_by": current_user.email
        }
        
    except Exception as e:
        await db.rollback()
        logger.error(f"❌ Error bulk verifying entries: {e}")
        raise HTTPException(status_code=500, detail=f"Verification failed: {str(e)}")


@router.get("/test/stardict-parser")
async def test_stardict_parser(
    dict_path: str = Query(..., description="Path to test StarDict files"),
    current_user: User = Depends(get_current_superuser)
):
    """
    Test StarDict parser without importing (Admin only)
    """
    try:
        logger.info(f"🧪 Admin {current_user.email} testing StarDict parser: {dict_path}")
        
        # Test parsing without import
        entries = stardict_service.parser.parse_stardict_files(dict_path)
        
        # Get sample entries
        sample_entries = entries[:5] if len(entries) > 5 else entries
        
        test_result = {
            "status": "success",
            "dictionary_info": stardict_service.parser.info_data,
            "total_entries": len(entries),
            "sample_entries": sample_entries,
            "parser_status": {
                "ifo_parsed": bool(stardict_service.parser.info_data),
                "idx_parsed": bool(stardict_service.parser.index_data),
                "dict_parsed": bool(stardict_service.parser.dict_data),
                "entries_extracted": len(entries) > 0
            },
            "tested_at": datetime.utcnow().isoformat()
        }
        
        logger.info(f"✅ StarDict parser test completed: {len(entries)} entries found")
        return test_result
        
    except Exception as e:
        logger.error(f"❌ StarDict parser test failed: {e}")
        raise HTTPException(status_code=500, detail=f"Parser test failed: {str(e)}")


async def _cleanup_upload_dir(upload_dir: Path):
    """
    Clean up uploaded files directory
    """
    try:
        import shutil
        if upload_dir.exists():
            shutil.rmtree(upload_dir)
            logger.info(f"🧹 Cleaned up upload directory: {upload_dir}")
    except Exception as e:
        logger.warning(f"⚠️ Failed to clean up upload directory: {e}")


# Add cleanup function to router for access
router._cleanup_upload_dir = _cleanup_upload_dir
