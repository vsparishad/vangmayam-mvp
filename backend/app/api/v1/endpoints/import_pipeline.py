"""
Import Pipeline API Endpoints for Vāṇmayam

This module provides REST API endpoints for:
- Archive.org integration and search
- Document import and processing
- OCR processing with Google Vision
- ALTO XML generation
- Batch processing workflows
"""

import asyncio
import logging
from typing import List, Optional, Dict, Any
from pathlib import Path
import tempfile
import shutil
from datetime import datetime

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, BackgroundTasks, Depends
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from ....services.archive_service import ArchiveOrgService, filter_vedic_texts
from ....services.document_processor import DocumentProcessor
from ....services.ocr_service import GoogleVisionOCRService, optimize_image_for_sanskrit_ocr
from ....core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()


# Pydantic models for request/response

class ArchiveSearchRequest(BaseModel):
    query: str = Field(..., description="Search query for Archive.org")
    collection: str = Field(default="texts", description="Archive.org collection")
    mediatype: str = Field(default="texts", description="Media type filter")
    limit: int = Field(default=50, ge=1, le=100, description="Maximum results")
    sort: str = Field(default="downloads desc", description="Sort order")


class ArchiveSearchResponse(BaseModel):
    query: str
    total_results: int
    results: List[Dict[str, Any]]
    filtered_results: List[Dict[str, Any]]
    processing_time: float


class ImportJobRequest(BaseModel):
    identifier: str = Field(..., description="Archive.org item identifier")
    download_files: bool = Field(default=True, description="Download files from Archive.org")
    process_documents: bool = Field(default=True, description="Process documents through pipeline")
    run_ocr: bool = Field(default=True, description="Run OCR processing")
    generate_alto: bool = Field(default=True, description="Generate ALTO XML")
    max_files: int = Field(default=5, ge=1, le=20, description="Maximum files to process")


class ImportJobResponse(BaseModel):
    job_id: str
    status: str
    identifier: str
    message: str
    created_at: str


class ProcessingStatus(BaseModel):
    job_id: str
    status: str
    progress: float
    current_step: str
    total_steps: int
    completed_steps: int
    results: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    updated_at: str


class OCRRequest(BaseModel):
    language_hints: List[str] = Field(default=["sa", "hi", "en"], description="Language hints for OCR")
    enhance_images: bool = Field(default=True, description="Enhance images before OCR")
    generate_alto: bool = Field(default=True, description="Generate ALTO XML output")


class OCRResponse(BaseModel):
    status: str
    results: List[Dict[str, Any]]
    processing_time: float
    total_images: int
    successful_images: int
    average_confidence: float


# In-memory job tracking (for MVP - would use Redis/database in production)
import_jobs: Dict[str, Dict[str, Any]] = {}


@router.get("/search", response_model=ArchiveSearchResponse)
async def search_archive_org(
    query: str,
    collection: str = "texts",
    mediatype: str = "texts",
    limit: int = 50,
    sort: str = "downloads desc"
):
    """
    Search Archive.org for Vedic literature and texts
    """
    try:
        start_time = datetime.utcnow()
        
        logger.info(f"🔍 Archive.org search request: {query}")
        
        async with ArchiveOrgService() as archive_service:
            # Perform search
            results = await archive_service.search_vedic_texts(
                query=query,
                collection=collection,
                mediatype=mediatype,
                limit=limit,
                sort=sort
            )
            
            # Filter for Vedic content
            filtered_results = filter_vedic_texts(results)
            
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            
            logger.info(f"✅ Search completed: {len(results)} total, {len(filtered_results)} filtered")
            
            return ArchiveSearchResponse(
                query=query,
                total_results=len(results),
                results=results,
                filtered_results=filtered_results,
                processing_time=processing_time
            )
            
    except Exception as e:
        logger.error(f"❌ Archive.org search failed: {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.get("/item/{identifier}")
async def get_archive_item_details(identifier: str):
    """
    Get detailed information about a specific Archive.org item
    """
    try:
        logger.info(f"📋 Getting item details: {identifier}")
        
        async with ArchiveOrgService() as archive_service:
            # Get metadata
            metadata = await archive_service.get_item_metadata(identifier)
            if not metadata:
                raise HTTPException(status_code=404, detail=f"Item not found: {identifier}")
            
            # Get file list
            files = await archive_service.list_item_files(identifier)
            
            result = {
                "identifier": identifier,
                "metadata": metadata,
                "files": files,
                "file_count": len(files),
                "retrieved_at": datetime.utcnow().isoformat()
            }
            
            logger.info(f"✅ Item details retrieved: {len(files)} files")
            return result
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to get item details: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get item details: {str(e)}")


@router.post("/import", response_model=ImportJobResponse)
async def start_import_job(
    request: ImportJobRequest,
    background_tasks: BackgroundTasks
):
    """
    Start an import job for processing an Archive.org item
    """
    try:
        import uuid
        job_id = str(uuid.uuid4())
        
        logger.info(f"🚀 Starting import job {job_id} for {request.identifier}")
        
        # Initialize job tracking
        import_jobs[job_id] = {
            "job_id": job_id,
            "status": "queued",
            "identifier": request.identifier,
            "request": request.dict(),
            "progress": 0.0,
            "current_step": "initializing",
            "total_steps": 5,
            "completed_steps": 0,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }
        
        # Start background processing
        background_tasks.add_task(
            process_import_job,
            job_id,
            request
        )
        
        return ImportJobResponse(
            job_id=job_id,
            status="queued",
            identifier=request.identifier,
            message="Import job queued for processing",
            created_at=import_jobs[job_id]["created_at"]
        )
        
    except Exception as e:
        logger.error(f"❌ Failed to start import job: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start import job: {str(e)}")


@router.get("/import/{job_id}/status", response_model=ProcessingStatus)
async def get_import_job_status(job_id: str):
    """
    Get the status of an import job
    """
    try:
        if job_id not in import_jobs:
            raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")
        
        job_data = import_jobs[job_id]
        
        return ProcessingStatus(
            job_id=job_id,
            status=job_data["status"],
            progress=job_data["progress"],
            current_step=job_data["current_step"],
            total_steps=job_data["total_steps"],
            completed_steps=job_data["completed_steps"],
            results=job_data.get("results"),
            error=job_data.get("error"),
            updated_at=job_data["updated_at"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to get job status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get job status: {str(e)}")


@router.post("/ocr/upload", response_model=OCRResponse)
async def process_uploaded_images(
    files: List[UploadFile] = File(...),
    language_hints: str = Form(default="sa,hi,en"),
    enhance_images: bool = Form(default=True),
    generate_alto: bool = Form(default=True)
):
    """
    Process uploaded images with OCR
    """
    try:
        start_time = datetime.utcnow()
        
        logger.info(f"📤 Processing {len(files)} uploaded images for OCR")
        
        # Parse language hints
        lang_hints = [lang.strip() for lang in language_hints.split(",")]
        
        # Create temporary directory for processing
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Save uploaded files
            image_paths = []
            for file in files:
                if not file.content_type.startswith('image/'):
                    continue
                
                file_path = temp_path / file.filename
                with open(file_path, 'wb') as f:
                    content = await file.read()
                    f.write(content)
                image_paths.append(file_path)
            
            if not image_paths:
                raise HTTPException(status_code=400, detail="No valid image files provided")
            
            # Process with OCR
            async with GoogleVisionOCRService() as ocr_service:
                options = {
                    "enhance_images": enhance_images,
                    "generate_alto_xml": generate_alto
                }
                
                results = await ocr_service.batch_process_images(
                    image_paths=image_paths,
                    output_dir=temp_path / "ocr_output",
                    language_hints=lang_hints,
                    options=options
                )
            
            # Calculate statistics
            successful_results = [r for r in results if r.get("status") == "success"]
            confidences = [r.get("confidence", 0) for r in successful_results if r.get("confidence", 0) > 0]
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
            
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            
            logger.info(f"✅ OCR processing completed: {len(successful_results)}/{len(results)} successful")
            
            return OCRResponse(
                status="completed",
                results=results,
                processing_time=processing_time,
                total_images=len(results),
                successful_images=len(successful_results),
                average_confidence=avg_confidence
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ OCR processing failed: {e}")
        raise HTTPException(status_code=500, detail=f"OCR processing failed: {str(e)}")


@router.get("/jobs")
async def list_import_jobs():
    """
    List all import jobs
    """
    try:
        jobs = []
        for job_id, job_data in import_jobs.items():
            jobs.append({
                "job_id": job_id,
                "status": job_data["status"],
                "identifier": job_data["identifier"],
                "progress": job_data["progress"],
                "created_at": job_data["created_at"],
                "updated_at": job_data["updated_at"]
            })
        
        # Sort by creation time (newest first)
        jobs.sort(key=lambda x: x["created_at"], reverse=True)
        
        return {
            "total_jobs": len(jobs),
            "jobs": jobs
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to list jobs: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list jobs: {str(e)}")


# Background task for processing import jobs
async def process_import_job(job_id: str, request: ImportJobRequest):
    """
    Background task to process an import job
    """
    try:
        logger.info(f"🔄 Processing import job {job_id}")
        
        # Update job status
        def update_job_status(status: str, step: str, progress: float, completed_steps: int, error: str = None):
            import_jobs[job_id].update({
                "status": status,
                "current_step": step,
                "progress": progress,
                "completed_steps": completed_steps,
                "updated_at": datetime.utcnow().isoformat()
            })
            if error:
                import_jobs[job_id]["error"] = error
        
        update_job_status("running", "fetching_metadata", 10.0, 1)
        
        # Create temporary directory for processing
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Step 1: Get item metadata and files
            async with ArchiveOrgService() as archive_service:
                metadata = await archive_service.get_item_metadata(request.identifier)
                if not metadata:
                    update_job_status("failed", "metadata_fetch_failed", 10.0, 1, "Item not found")
                    return
                
                files = await archive_service.list_item_files(request.identifier)
                if not files:
                    update_job_status("failed", "no_files_found", 20.0, 1, "No processable files found")
                    return
                
                update_job_status("running", "downloading_files", 30.0, 2)
                
                # Step 2: Download files (if requested)
                downloaded_files = []
                if request.download_files:
                    files_to_download = files[:request.max_files]
                    for i, file_info in enumerate(files_to_download):
                        filename = file_info.get("name")
                        if filename:
                            downloaded_path = await archive_service.download_file(
                                request.identifier,
                                filename,
                                temp_path / "downloads"
                            )
                            if downloaded_path:
                                downloaded_files.append(downloaded_path)
                        
                        # Update progress
                        progress = 30.0 + (i + 1) / len(files_to_download) * 20.0
                        update_job_status("running", f"downloading_file_{i+1}", progress, 2)
                
                update_job_status("running", "processing_documents", 60.0, 3)
                
                # Step 3: Process documents (if requested)
                processed_docs = []
                if request.process_documents and downloaded_files:
                    processor = DocumentProcessor()
                    
                    for i, file_path in enumerate(downloaded_files):
                        if processor.is_supported_format(file_path):
                            doc_output_dir = temp_path / "processed" / file_path.stem
                            result = await processor.process_document(
                                file_path,
                                doc_output_dir,
                                {"enhance_images": True, "dpi": 300}
                            )
                            processed_docs.append(result)
                        
                        # Update progress
                        progress = 60.0 + (i + 1) / len(downloaded_files) * 20.0
                        update_job_status("running", f"processing_doc_{i+1}", progress, 3)
                
                update_job_status("running", "running_ocr", 80.0, 4)
                
                # Step 4: Run OCR (if requested)
                ocr_results = []
                if request.run_ocr and processed_docs:
                    async with GoogleVisionOCRService() as ocr_service:
                        for doc_result in processed_docs:
                            if doc_result.get("status") == "completed":
                                pages = doc_result.get("pages", [])
                                image_paths = [Path(page["image_path"]) for page in pages]
                                
                                if image_paths:
                                    options = optimize_image_for_sanskrit_ocr(image_paths[0])
                                    options["generate_alto_xml"] = request.generate_alto
                                    
                                    batch_results = await ocr_service.batch_process_images(
                                        image_paths,
                                        temp_path / "ocr_output",
                                        options.get("language_hints"),
                                        options
                                    )
                                    ocr_results.extend(batch_results)
                
                update_job_status("running", "finalizing", 95.0, 5)
                
                # Step 5: Finalize results
                final_results = {
                    "identifier": request.identifier,
                    "metadata": metadata,
                    "files": files,
                    "downloaded_files": [str(p) for p in downloaded_files],
                    "processed_documents": processed_docs,
                    "ocr_results": ocr_results,
                    "statistics": {
                        "total_files": len(files),
                        "downloaded_files": len(downloaded_files),
                        "processed_documents": len(processed_docs),
                        "ocr_pages": len(ocr_results),
                        "successful_ocr": len([r for r in ocr_results if r.get("status") == "success"])
                    },
                    "completed_at": datetime.utcnow().isoformat()
                }
                
                import_jobs[job_id]["results"] = final_results
                update_job_status("completed", "finished", 100.0, 5)
                
                logger.info(f"✅ Import job {job_id} completed successfully")
        
    except Exception as e:
        logger.error(f"❌ Import job {job_id} failed: {e}")
        update_job_status("failed", "processing_error", 0.0, 0, str(e))
