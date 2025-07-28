"""
Google Vision OCR Service for Vāṇmayam

This service handles:
- Google Cloud Vision API integration
- OCR processing of document images
- ALTO XML standardization and output
- Sanskrit text recognition optimization
- Batch processing with rate limiting
"""

import asyncio
import logging
from typing import List, Optional, Dict, Any, Tuple
from pathlib import Path
import json
from datetime import datetime
import xml.etree.ElementTree as ET
from xml.dom import minidom
import base64

# Google Cloud Vision
try:
    from google.cloud import vision
    from google.oauth2 import service_account
    VISION_AVAILABLE = True
except ImportError:
    VISION_AVAILABLE = False
    logging.warning("Google Cloud Vision not available - OCR processing disabled")

from ..core.config import settings

logger = logging.getLogger(__name__)


class GoogleVisionOCRService:
    """Service for OCR processing using Google Cloud Vision API"""
    
    def __init__(self, credentials_path: Optional[Path] = None):
        self.credentials_path = credentials_path
        self.client: Optional[vision.ImageAnnotatorClient] = None
        self.rate_limit_delay = 1.0  # Seconds between API calls
        
        # ALTO XML namespace and schema info
        self.alto_namespace = {
            "alto": "http://www.loc.gov/standards/alto/ns-v4#",
            "xsi": "http://www.w3.org/2001/XMLSchema-instance"
        }
        
    async def __aenter__(self):
        """Async context manager entry"""
        await self.initialize_client()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        # Google Vision client doesn't need explicit cleanup
        pass
    
    async def initialize_client(self):
        """Initialize Google Vision API client"""
        if not VISION_AVAILABLE:
            raise RuntimeError("Google Cloud Vision not available - install google-cloud-vision")
        
        try:
            if self.credentials_path and self.credentials_path.exists():
                credentials = service_account.Credentials.from_service_account_file(
                    str(self.credentials_path)
                )
                self.client = vision.ImageAnnotatorClient(credentials=credentials)
                logger.info(f"✅ Google Vision client initialized with credentials: {self.credentials_path}")
            else:
                # Use default credentials (environment variable or gcloud auth)
                self.client = vision.ImageAnnotatorClient()
                logger.info("✅ Google Vision client initialized with default credentials")
                
        except Exception as e:
            logger.error(f"❌ Failed to initialize Google Vision client: {e}")
            raise
    
    async def process_image_ocr(
        self,
        image_path: Path,
        language_hints: Optional[List[str]] = None,
        options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process a single image with Google Vision OCR
        
        Args:
            image_path: Path to image file
            language_hints: List of language codes (e.g., ['sa', 'en'] for Sanskrit and English)
            options: Additional OCR options
            
        Returns:
            OCR results with text, confidence, and bounding boxes
        """
        try:
            if not self.client:
                await self.initialize_client()
            
            logger.info(f"🔍 Processing OCR for: {image_path.name}")
            
            # Read image file
            with open(image_path, 'rb') as image_file:
                content = image_file.read()
            
            # Create Vision API image object
            image = vision.Image(content=content)
            
            # Configure OCR features
            features = [vision.Feature(type_=vision.Feature.Type.DOCUMENT_TEXT_DETECTION)]
            
            # Set up image context with language hints
            image_context = vision.ImageContext()
            if language_hints:
                image_context.language_hints = language_hints
            
            # Create request
            request = vision.AnnotateImageRequest(
                image=image,
                features=features,
                image_context=image_context
            )
            
            # Make API call
            response = await asyncio.get_event_loop().run_in_executor(
                None, self.client.annotate_image, request
            )
            
            if response.error.message:
                raise Exception(f"Vision API error: {response.error.message}")
            
            # Process response
            result = await self._process_vision_response(response, image_path, options or {})
            
            # Add rate limiting delay
            await asyncio.sleep(self.rate_limit_delay)
            
            logger.info(f"✅ OCR completed for {image_path.name}: {len(result.get('words', []))} words detected")
            return result
            
        except Exception as e:
            logger.error(f"❌ OCR processing failed for {image_path}: {e}")
            return {
                "image_path": str(image_path),
                "error": str(e),
                "status": "failed",
                "processed_at": datetime.utcnow().isoformat()
            }
    
    async def _process_vision_response(
        self,
        response: vision.AnnotateImageResponse,
        image_path: Path,
        options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process Google Vision API response into structured format"""
        try:
            # Get full text annotation
            full_text = response.full_text_annotation
            
            if not full_text:
                return {
                    "image_path": str(image_path),
                    "text": "",
                    "confidence": 0.0,
                    "words": [],
                    "lines": [],
                    "paragraphs": [],
                    "blocks": [],
                    "status": "no_text_detected",
                    "processed_at": datetime.utcnow().isoformat()
                }
            
            # Extract text content
            detected_text = full_text.text
            
            # Process text structure
            words = []
            lines = []
            paragraphs = []
            blocks = []
            
            for page in full_text.pages:
                for block in page.blocks:
                    block_info = {
                        "block_type": block.block_type.name,
                        "confidence": block.confidence,
                        "bounding_box": self._extract_bounding_box(block.bounding_box),
                        "paragraphs": []
                    }
                    
                    for paragraph in block.paragraphs:
                        paragraph_info = {
                            "confidence": paragraph.confidence,
                            "bounding_box": self._extract_bounding_box(paragraph.bounding_box),
                            "words": []
                        }
                        
                        paragraph_text = ""
                        
                        for word in paragraph.words:
                            word_text = "".join([symbol.text for symbol in word.symbols])
                            word_confidence = word.confidence
                            
                            word_info = {
                                "text": word_text,
                                "confidence": word_confidence,
                                "bounding_box": self._extract_bounding_box(word.bounding_box),
                                "symbols": []
                            }
                            
                            # Extract symbol-level information
                            for symbol in word.symbols:
                                symbol_info = {
                                    "text": symbol.text,
                                    "confidence": symbol.confidence,
                                    "bounding_box": self._extract_bounding_box(symbol.bounding_box)
                                }
                                word_info["symbols"].append(symbol_info)
                            
                            words.append(word_info)
                            paragraph_info["words"].append(word_info)
                            paragraph_text += word_text + " "
                        
                        paragraph_info["text"] = paragraph_text.strip()
                        paragraphs.append(paragraph_info)
                        block_info["paragraphs"].append(paragraph_info)
                    
                    blocks.append(block_info)
            
            # Calculate overall confidence
            word_confidences = [w["confidence"] for w in words if w["confidence"] > 0]
            overall_confidence = sum(word_confidences) / len(word_confidences) if word_confidences else 0.0
            
            result = {
                "image_path": str(image_path),
                "text": detected_text,
                "confidence": overall_confidence,
                "words": words,
                "lines": lines,  # Lines can be extracted from paragraphs if needed
                "paragraphs": paragraphs,
                "blocks": blocks,
                "language_detected": self._detect_languages(detected_text),
                "status": "success",
                "processed_at": datetime.utcnow().isoformat(),
                "word_count": len(words),
                "character_count": len(detected_text)
            }
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Error processing Vision response: {e}")
            raise
    
    def _extract_bounding_box(self, bounding_box) -> Dict[str, int]:
        """Extract bounding box coordinates"""
        vertices = bounding_box.vertices
        return {
            "x_min": min(v.x for v in vertices),
            "y_min": min(v.y for v in vertices),
            "x_max": max(v.x for v in vertices),
            "y_max": max(v.y for v in vertices),
            "width": max(v.x for v in vertices) - min(v.x for v in vertices),
            "height": max(v.y for v in vertices) - min(v.y for v in vertices)
        }
    
    def _detect_languages(self, text: str) -> List[str]:
        """Detect languages in the text (basic implementation)"""
        languages = []
        
        # Check for Sanskrit/Devanagari characters
        if any('\u0900' <= char <= '\u097F' for char in text):
            languages.append("sanskrit")
        
        # Check for English characters
        if any('a' <= char.lower() <= 'z' for char in text):
            languages.append("english")
        
        return languages or ["unknown"]
    
    async def convert_to_alto_xml(
        self,
        ocr_result: Dict[str, Any],
        output_path: Path,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Path:
        """
        Convert OCR results to ALTO XML format
        
        Args:
            ocr_result: OCR processing results
            output_path: Path for ALTO XML output
            metadata: Additional metadata for the document
            
        Returns:
            Path to generated ALTO XML file
        """
        try:
            logger.info(f"📄 Converting OCR results to ALTO XML: {output_path.name}")
            
            # Create ALTO XML structure
            alto_root = ET.Element("alto")
            alto_root.set("xmlns", self.alto_namespace["alto"])
            alto_root.set("xmlns:xsi", self.alto_namespace["xsi"])
            alto_root.set("xsi:schemaLocation", 
                         "http://www.loc.gov/standards/alto/ns-v4# http://www.loc.gov/standards/alto/v4/alto-4-2.xsd")
            
            # Description section
            description = ET.SubElement(alto_root, "Description")
            
            # Measurement unit
            measurement_unit = ET.SubElement(description, "MeasurementUnit")
            measurement_unit.text = "pixel"
            
            # Source image information
            source_image_info = ET.SubElement(description, "sourceImageInformation")
            file_name = ET.SubElement(source_image_info, "fileName")
            file_name.text = Path(ocr_result["image_path"]).name
            
            # OCR processing information
            ocr_processing = ET.SubElement(description, "OCRProcessing")
            ocr_processing.set("ID", "OCR_1")
            
            ocr_software = ET.SubElement(ocr_processing, "ocrProcessingStep")
            processing_software = ET.SubElement(ocr_software, "processingSoftware")
            software_creator = ET.SubElement(processing_software, "softwareCreator")
            software_creator.text = "Google Cloud Vision API"
            software_name = ET.SubElement(processing_software, "softwareName")
            software_name.text = "Google Vision OCR"
            processing_date = ET.SubElement(ocr_software, "processingDateTime")
            processing_date.text = ocr_result.get("processed_at", datetime.utcnow().isoformat())
            
            # Layout section
            layout = ET.SubElement(alto_root, "Layout")
            
            # Page
            page = ET.SubElement(layout, "Page")
            page.set("ID", "PAGE_1")
            page.set("PHYSICAL_IMG_NR", "1")
            
            # Get image dimensions (approximate from bounding boxes)
            max_x = max_y = 0
            for block in ocr_result.get("blocks", []):
                bbox = block.get("bounding_box", {})
                max_x = max(max_x, bbox.get("x_max", 0))
                max_y = max(max_y, bbox.get("y_max", 0))
            
            page.set("WIDTH", str(max_x))
            page.set("HEIGHT", str(max_y))
            
            # Print space (main content area)
            print_space = ET.SubElement(page, "PrintSpace")
            print_space.set("HPOS", "0")
            print_space.set("VPOS", "0")
            print_space.set("WIDTH", str(max_x))
            print_space.set("HEIGHT", str(max_y))
            
            # Process blocks
            for block_idx, block in enumerate(ocr_result.get("blocks", [])):
                text_block = ET.SubElement(print_space, "TextBlock")
                text_block.set("ID", f"BLOCK_{block_idx + 1}")
                
                bbox = block.get("bounding_box", {})
                text_block.set("HPOS", str(bbox.get("x_min", 0)))
                text_block.set("VPOS", str(bbox.get("y_min", 0)))
                text_block.set("WIDTH", str(bbox.get("width", 0)))
                text_block.set("HEIGHT", str(bbox.get("height", 0)))
                
                # Process paragraphs
                for para_idx, paragraph in enumerate(block.get("paragraphs", [])):
                    text_line = ET.SubElement(text_block, "TextLine")
                    text_line.set("ID", f"LINE_{block_idx + 1}_{para_idx + 1}")
                    
                    para_bbox = paragraph.get("bounding_box", {})
                    text_line.set("HPOS", str(para_bbox.get("x_min", 0)))
                    text_line.set("VPOS", str(para_bbox.get("y_min", 0)))
                    text_line.set("WIDTH", str(para_bbox.get("width", 0)))
                    text_line.set("HEIGHT", str(para_bbox.get("height", 0)))
                    
                    # Process words
                    for word_idx, word in enumerate(paragraph.get("words", [])):
                        string_elem = ET.SubElement(text_line, "String")
                        string_elem.set("ID", f"WORD_{block_idx + 1}_{para_idx + 1}_{word_idx + 1}")
                        string_elem.set("CONTENT", word.get("text", ""))
                        string_elem.set("WC", f"{word.get('confidence', 0.0):.3f}")
                        
                        word_bbox = word.get("bounding_box", {})
                        string_elem.set("HPOS", str(word_bbox.get("x_min", 0)))
                        string_elem.set("VPOS", str(word_bbox.get("y_min", 0)))
                        string_elem.set("WIDTH", str(word_bbox.get("width", 0)))
                        string_elem.set("HEIGHT", str(word_bbox.get("height", 0)))
                        
                        # Add space element between words (except last word)
                        if word_idx < len(paragraph.get("words", [])) - 1:
                            space_elem = ET.SubElement(text_line, "SP")
                            space_elem.set("WIDTH", "5")  # Approximate space width
            
            # Create output directory if needed
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write ALTO XML with pretty formatting
            xml_str = ET.tostring(alto_root, encoding='unicode')
            dom = minidom.parseString(xml_str)
            pretty_xml = dom.toprettyxml(indent="  ")
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(pretty_xml)
            
            logger.info(f"✅ ALTO XML generated: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"❌ Error generating ALTO XML: {e}")
            raise
    
    async def batch_process_images(
        self,
        image_paths: List[Path],
        output_dir: Path,
        language_hints: Optional[List[str]] = None,
        options: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Process multiple images with OCR in batch
        
        Args:
            image_paths: List of image file paths
            output_dir: Directory for OCR outputs
            language_hints: Language hints for OCR
            options: Processing options
            
        Returns:
            List of OCR results
        """
        try:
            logger.info(f"📚 Starting batch OCR processing: {len(image_paths)} images")
            
            # Create output directory
            output_dir.mkdir(parents=True, exist_ok=True)
            
            results = []
            generate_alto = options.get("generate_alto_xml", True) if options else True
            
            for i, image_path in enumerate(image_paths, 1):
                logger.info(f"🔍 Processing image {i}/{len(image_paths)}: {image_path.name}")
                
                # Process OCR
                ocr_result = await self.process_image_ocr(image_path, language_hints, options)
                
                if ocr_result.get("status") == "success" and generate_alto:
                    # Generate ALTO XML
                    alto_filename = f"{image_path.stem}_alto.xml"
                    alto_path = output_dir / alto_filename
                    
                    try:
                        alto_xml_path = await self.convert_to_alto_xml(ocr_result, alto_path)
                        ocr_result["alto_xml_path"] = str(alto_xml_path)
                    except Exception as e:
                        logger.error(f"❌ Failed to generate ALTO XML for {image_path.name}: {e}")
                        ocr_result["alto_xml_error"] = str(e)
                
                results.append(ocr_result)
                
                # Progress logging
                if i % 10 == 0:
                    logger.info(f"📊 Batch progress: {i}/{len(image_paths)} images processed")
            
            logger.info(f"✅ Batch OCR processing completed: {len(results)} images processed")
            return results
            
        except Exception as e:
            logger.error(f"❌ Error in batch OCR processing: {e}")
            return []


# Utility functions for OCR processing

def optimize_image_for_sanskrit_ocr(image_path: Path) -> Dict[str, Any]:
    """
    Get optimal settings for Sanskrit text OCR
    
    Args:
        image_path: Path to image file
        
    Returns:
        Optimized OCR options for Sanskrit text
    """
    return {
        "language_hints": ["sa", "hi", "en"],  # Sanskrit, Hindi, English
        "enhance_images": True,
        "denoise": True,
        "enhance_contrast": True,
        "binarize": True,
        "dpi": 300,
        "generate_alto_xml": True
    }


def calculate_ocr_confidence_score(ocr_results: List[Dict[str, Any]]) -> float:
    """
    Calculate overall confidence score for a batch of OCR results
    
    Args:
        ocr_results: List of OCR processing results
        
    Returns:
        Overall confidence score (0.0 to 1.0)
    """
    if not ocr_results:
        return 0.0
    
    total_confidence = 0.0
    valid_results = 0
    
    for result in ocr_results:
        if result.get("status") == "success" and "confidence" in result:
            total_confidence += result["confidence"]
            valid_results += 1
    
    return total_confidence / valid_results if valid_results > 0 else 0.0


def extract_sanskrit_text_statistics(ocr_results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Extract statistics specific to Sanskrit text processing
    
    Args:
        ocr_results: List of OCR processing results
        
    Returns:
        Sanskrit text statistics
    """
    stats = {
        "total_pages": len(ocr_results),
        "successful_pages": 0,
        "total_words": 0,
        "total_characters": 0,
        "sanskrit_pages": 0,
        "average_confidence": 0.0,
        "devanagari_character_count": 0
    }
    
    confidences = []
    
    for result in ocr_results:
        if result.get("status") == "success":
            stats["successful_pages"] += 1
            stats["total_words"] += result.get("word_count", 0)
            stats["total_characters"] += result.get("character_count", 0)
            
            if result.get("confidence", 0) > 0:
                confidences.append(result["confidence"])
            
            # Check for Sanskrit/Devanagari content
            text = result.get("text", "")
            if any('\u0900' <= char <= '\u097F' for char in text):
                stats["sanskrit_pages"] += 1
                stats["devanagari_character_count"] += sum(
                    1 for char in text if '\u0900' <= char <= '\u097F'
                )
    
    if confidences:
        stats["average_confidence"] = sum(confidences) / len(confidences)
    
    return stats
