"""
Document Processing Pipeline for Vāṇmayam

This service handles:
- PDF to image conversion
- Image preprocessing and optimization
- Multi-format document handling
- Preparation for OCR processing
- Integration with Celery for async processing
"""

import asyncio
import logging
from typing import List, Optional, Dict, Any, Tuple
from pathlib import Path
import tempfile
import shutil
from datetime import datetime
import json

# PDF processing
try:
    import fitz  # PyMuPDF
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False
    logging.warning("PyMuPDF not available - PDF processing disabled")

# Image processing
try:
    from PIL import Image, ImageEnhance, ImageFilter
    import cv2
    import numpy as np
    IMAGE_PROCESSING_AVAILABLE = True
except ImportError:
    IMAGE_PROCESSING_AVAILABLE = False
    logging.warning("PIL/OpenCV not available - advanced image processing disabled")

from ..core.config import settings

logger = logging.getLogger(__name__)


class DocumentProcessor:
    """Service for processing documents in the import pipeline"""
    
    def __init__(self, temp_dir: Optional[Path] = None):
        self.temp_dir = temp_dir or Path(tempfile.gettempdir()) / "vangmayam_processing"
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        
        # Supported formats
        self.supported_pdf_formats = [".pdf"]
        self.supported_image_formats = [".png", ".jpg", ".jpeg", ".tiff", ".tif", ".bmp"]
        
    def is_supported_format(self, file_path: Path) -> bool:
        """Check if file format is supported for processing"""
        suffix = file_path.suffix.lower()
        return suffix in (self.supported_pdf_formats + self.supported_image_formats)
    
    async def process_document(
        self,
        input_path: Path,
        output_dir: Path,
        options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process a document through the complete pipeline
        
        Args:
            input_path: Path to input document
            output_dir: Directory for processed outputs
            options: Processing options
            
        Returns:
            Processing results with metadata
        """
        try:
            logger.info(f"📄 Processing document: {input_path.name}")
            
            if not input_path.exists():
                raise FileNotFoundError(f"Input file not found: {input_path}")
            
            if not self.is_supported_format(input_path):
                raise ValueError(f"Unsupported format: {input_path.suffix}")
            
            # Create output directory
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Initialize processing results
            results = {
                "input_file": str(input_path),
                "output_dir": str(output_dir),
                "processing_started": datetime.utcnow().isoformat(),
                "pages": [],
                "metadata": {},
                "status": "processing"
            }
            
            # Process based on file type
            if input_path.suffix.lower() == ".pdf":
                results = await self._process_pdf(input_path, output_dir, options or {})
            else:
                results = await self._process_image(input_path, output_dir, options or {})
            
            results["processing_completed"] = datetime.utcnow().isoformat()
            results["status"] = "completed"
            
            logger.info(f"✅ Document processing completed: {len(results.get('pages', []))} pages")
            return results
            
        except Exception as e:
            logger.error(f"❌ Error processing document {input_path}: {e}")
            return {
                "input_file": str(input_path),
                "error": str(e),
                "status": "failed",
                "processing_failed": datetime.utcnow().isoformat()
            }
    
    async def _process_pdf(
        self,
        pdf_path: Path,
        output_dir: Path,
        options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process PDF document to images"""
        if not PDF_AVAILABLE:
            raise RuntimeError("PDF processing not available - PyMuPDF not installed")
        
        try:
            logger.info(f"📖 Processing PDF: {pdf_path.name}")
            
            # Open PDF document
            doc = fitz.open(str(pdf_path))
            
            results = {
                "input_file": str(pdf_path),
                "output_dir": str(output_dir),
                "document_type": "pdf",
                "total_pages": len(doc),
                "pages": [],
                "metadata": {
                    "title": doc.metadata.get("title", ""),
                    "author": doc.metadata.get("author", ""),
                    "subject": doc.metadata.get("subject", ""),
                    "creator": doc.metadata.get("creator", ""),
                    "creation_date": doc.metadata.get("creationDate", ""),
                    "modification_date": doc.metadata.get("modDate", "")
                }
            }
            
            # Processing options
            dpi = options.get("dpi", 300)
            image_format = options.get("image_format", "png")
            max_pages = options.get("max_pages", None)
            
            # Convert each page to image
            pages_to_process = min(len(doc), max_pages) if max_pages else len(doc)
            
            for page_num in range(pages_to_process):
                page = doc[page_num]
                
                # Convert page to image
                mat = fitz.Matrix(dpi/72, dpi/72)  # Scale factor for DPI
                pix = page.get_pixmap(matrix=mat)
                
                # Save image
                image_filename = f"page_{page_num + 1:04d}.{image_format}"
                image_path = output_dir / image_filename
                
                pix.save(str(image_path))
                
                # Process image if enhancement is enabled
                if options.get("enhance_images", True) and IMAGE_PROCESSING_AVAILABLE:
                    enhanced_path = await self._enhance_image(image_path, options)
                    if enhanced_path:
                        image_path = enhanced_path
                
                page_info = {
                    "page_number": page_num + 1,
                    "image_path": str(image_path),
                    "image_format": image_format,
                    "dpi": dpi,
                    "width": pix.width,
                    "height": pix.height,
                    "file_size": image_path.stat().st_size if image_path.exists() else 0
                }
                
                results["pages"].append(page_info)
                
                logger.info(f"📄 Processed page {page_num + 1}/{pages_to_process}")
            
            doc.close()
            
            logger.info(f"✅ PDF processing completed: {len(results['pages'])} pages")
            return results
            
        except Exception as e:
            logger.error(f"❌ Error processing PDF {pdf_path}: {e}")
            raise
    
    async def _process_image(
        self,
        image_path: Path,
        output_dir: Path,
        options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process single image file"""
        try:
            logger.info(f"🖼️ Processing image: {image_path.name}")
            
            if not IMAGE_PROCESSING_AVAILABLE:
                # Simple copy if no processing available
                output_path = output_dir / image_path.name
                shutil.copy2(image_path, output_path)
                
                return {
                    "input_file": str(image_path),
                    "output_dir": str(output_dir),
                    "document_type": "image",
                    "total_pages": 1,
                    "pages": [{
                        "page_number": 1,
                        "image_path": str(output_path),
                        "image_format": image_path.suffix[1:],
                        "file_size": output_path.stat().st_size
                    }],
                    "metadata": {}
                }
            
            # Load image for processing
            with Image.open(image_path) as img:
                # Get image metadata
                metadata = {
                    "format": img.format,
                    "mode": img.mode,
                    "size": img.size,
                    "dpi": img.info.get("dpi", (72, 72))
                }
                
                # Process image if enhancement is enabled
                output_path = output_dir / f"processed_{image_path.name}"
                
                if options.get("enhance_images", True):
                    enhanced_path = await self._enhance_image(image_path, options)
                    if enhanced_path:
                        output_path = enhanced_path
                    else:
                        shutil.copy2(image_path, output_path)
                else:
                    shutil.copy2(image_path, output_path)
                
                results = {
                    "input_file": str(image_path),
                    "output_dir": str(output_dir),
                    "document_type": "image",
                    "total_pages": 1,
                    "pages": [{
                        "page_number": 1,
                        "image_path": str(output_path),
                        "image_format": output_path.suffix[1:],
                        "width": metadata["size"][0],
                        "height": metadata["size"][1],
                        "dpi": metadata["dpi"][0] if isinstance(metadata["dpi"], tuple) else metadata["dpi"],
                        "file_size": output_path.stat().st_size if output_path.exists() else 0
                    }],
                    "metadata": metadata
                }
                
                logger.info(f"✅ Image processing completed")
                return results
                
        except Exception as e:
            logger.error(f"❌ Error processing image {image_path}: {e}")
            raise
    
    async def _enhance_image(
        self,
        image_path: Path,
        options: Dict[str, Any]
    ) -> Optional[Path]:
        """Enhance image for better OCR results"""
        if not IMAGE_PROCESSING_AVAILABLE:
            return None
        
        try:
            logger.info(f"✨ Enhancing image: {image_path.name}")
            
            # Load image
            img = cv2.imread(str(image_path))
            if img is None:
                logger.warning(f"⚠️ Could not load image for enhancement: {image_path}")
                return None
            
            # Convert to grayscale
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
            # Apply enhancement techniques
            enhanced = gray
            
            # Noise reduction
            if options.get("denoise", True):
                enhanced = cv2.fastNlMeansDenoising(enhanced)
            
            # Contrast enhancement
            if options.get("enhance_contrast", True):
                clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
                enhanced = clahe.apply(enhanced)
            
            # Sharpening
            if options.get("sharpen", True):
                kernel = np.array([[-1,-1,-1], [-1,9,-1], [-1,-1,-1]])
                enhanced = cv2.filter2D(enhanced, -1, kernel)
            
            # Binarization for text documents
            if options.get("binarize", True):
                _, enhanced = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            # Save enhanced image
            enhanced_path = image_path.parent / f"enhanced_{image_path.name}"
            cv2.imwrite(str(enhanced_path), enhanced)
            
            logger.info(f"✅ Image enhancement completed: {enhanced_path.name}")
            return enhanced_path
            
        except Exception as e:
            logger.error(f"❌ Error enhancing image {image_path}: {e}")
            return None
    
    async def batch_process_documents(
        self,
        input_paths: List[Path],
        output_base_dir: Path,
        options: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Process multiple documents in batch
        
        Args:
            input_paths: List of input document paths
            output_base_dir: Base directory for outputs
            options: Processing options
            
        Returns:
            List of processing results
        """
        try:
            logger.info(f"📚 Starting batch processing: {len(input_paths)} documents")
            
            results = []
            
            for i, input_path in enumerate(input_paths, 1):
                logger.info(f"📄 Processing document {i}/{len(input_paths)}: {input_path.name}")
                
                # Create unique output directory for each document
                doc_output_dir = output_base_dir / f"doc_{i:04d}_{input_path.stem}"
                
                # Process document
                result = await self.process_document(input_path, doc_output_dir, options)
                results.append(result)
                
                # Add small delay to prevent overwhelming the system
                await asyncio.sleep(0.1)
            
            logger.info(f"✅ Batch processing completed: {len(results)} documents processed")
            return results
            
        except Exception as e:
            logger.error(f"❌ Error in batch processing: {e}")
            return []
    
    def cleanup_temp_files(self):
        """Clean up temporary processing files"""
        try:
            if self.temp_dir.exists():
                shutil.rmtree(self.temp_dir)
                logger.info(f"🧹 Cleaned up temporary files: {self.temp_dir}")
        except Exception as e:
            logger.error(f"❌ Error cleaning up temp files: {e}")


# Utility functions for document processing

def get_optimal_dpi_for_ocr(image_size: Tuple[int, int], target_dpi: int = 300) -> int:
    """
    Calculate optimal DPI for OCR based on image size
    
    Args:
        image_size: (width, height) of image in pixels
        target_dpi: Target DPI for OCR
        
    Returns:
        Recommended DPI value
    """
    width, height = image_size
    
    # For very large images, reduce DPI to avoid memory issues
    if width > 4000 or height > 4000:
        return 200
    elif width > 2000 or height > 2000:
        return 250
    else:
        return target_dpi


def estimate_processing_time(
    file_paths: List[Path],
    options: Dict[str, Any]
) -> float:
    """
    Estimate processing time for a batch of documents
    
    Args:
        file_paths: List of document paths
        options: Processing options
        
    Returns:
        Estimated processing time in seconds
    """
    total_time = 0.0
    
    for file_path in file_paths:
        if not file_path.exists():
            continue
        
        file_size_mb = file_path.stat().st_size / (1024 * 1024)
        
        if file_path.suffix.lower() == ".pdf":
            # Estimate based on file size (rough approximation)
            estimated_pages = max(1, int(file_size_mb / 0.5))  # ~0.5MB per page
            time_per_page = 2.0 if options.get("enhance_images", True) else 1.0
            total_time += estimated_pages * time_per_page
        else:
            # Image processing time
            time_per_image = 1.0 if options.get("enhance_images", True) else 0.2
            total_time += time_per_image
    
    return total_time
