"""
Archive.org Integration Service for Vāṇmayam

This service handles:
- Searching and retrieving Vedic literature from Archive.org
- Downloading PDF/image files
- Metadata extraction and validation
- Integration with the import pipeline
"""

import asyncio
import aiohttp
import logging
from typing import Dict, List, Optional, Any
from pathlib import Path
import json
from datetime import datetime

from ..core.config import settings

logger = logging.getLogger(__name__)


class ArchiveOrgService:
    """Service for integrating with Archive.org Internet Archive"""
    
    BASE_URL = "https://archive.org"
    SEARCH_URL = f"{BASE_URL}/advancedsearch.php"
    DOWNLOAD_URL = f"{BASE_URL}/download"
    METADATA_URL = f"{BASE_URL}/metadata"
    
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        
    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=300),  # 5 minutes timeout
            headers={
                "User-Agent": "Vangmayam-MVP/1.0 (Digital Preservation Platform)"
            }
        )
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
    
    async def search_vedic_texts(
        self,
        query: str = "vedic OR sanskrit OR hinduism",
        collection: str = "texts",
        mediatype: str = "texts",
        limit: int = 50,
        sort: str = "downloads desc"
    ) -> List[Dict[str, Any]]:
        """
        Search for Vedic texts on Archive.org
        
        Args:
            query: Search query string
            collection: Archive.org collection to search
            mediatype: Type of media (texts, image, etc.)
            limit: Maximum number of results
            sort: Sort order
            
        Returns:
            List of search results with metadata
        """
        try:
            params = {
                "q": f"({query}) AND collection:({collection}) AND mediatype:({mediatype})",
                "fl": "identifier,title,creator,description,date,downloads,format,language,subject",
                "rows": limit,
                "sort": sort,
                "output": "json"
            }
            
            logger.info(f"🔍 Searching Archive.org for: {query}")
            
            async with self.session.get(self.SEARCH_URL, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    results = data.get("response", {}).get("docs", [])
                    
                    logger.info(f"✅ Found {len(results)} results from Archive.org")
                    return results
                else:
                    logger.error(f"❌ Archive.org search failed: {response.status}")
                    return []
                    
        except Exception as e:
            logger.error(f"❌ Error searching Archive.org: {e}")
            return []
    
    async def get_item_metadata(self, identifier: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed metadata for a specific Archive.org item
        
        Args:
            identifier: Archive.org item identifier
            
        Returns:
            Item metadata dictionary or None if failed
        """
        try:
            url = f"{self.METADATA_URL}/{identifier}"
            
            logger.info(f"📋 Fetching metadata for: {identifier}")
            
            async with self.session.get(url) as response:
                if response.status == 200:
                    metadata = await response.json()
                    logger.info(f"✅ Retrieved metadata for {identifier}")
                    return metadata
                else:
                    logger.error(f"❌ Failed to get metadata for {identifier}: {response.status}")
                    return None
                    
        except Exception as e:
            logger.error(f"❌ Error getting metadata for {identifier}: {e}")
            return None
    
    async def list_item_files(self, identifier: str) -> List[Dict[str, Any]]:
        """
        List all files available for an Archive.org item
        
        Args:
            identifier: Archive.org item identifier
            
        Returns:
            List of file information dictionaries
        """
        try:
            metadata = await self.get_item_metadata(identifier)
            if not metadata:
                return []
            
            files = metadata.get("files", [])
            
            # Filter for relevant file types (PDF, images)
            relevant_files = []
            for file_info in files:
                format_type = file_info.get("format", "").lower()
                if format_type in ["pdf", "png", "jpeg", "jpg", "tiff", "tif"]:
                    relevant_files.append(file_info)
            
            logger.info(f"📁 Found {len(relevant_files)} relevant files for {identifier}")
            return relevant_files
            
        except Exception as e:
            logger.error(f"❌ Error listing files for {identifier}: {e}")
            return []
    
    async def download_file(
        self,
        identifier: str,
        filename: str,
        download_path: Path,
        progress_callback: Optional[callable] = None
    ) -> Optional[Path]:
        """
        Download a specific file from Archive.org
        
        Args:
            identifier: Archive.org item identifier
            filename: Name of file to download
            download_path: Local path to save the file
            progress_callback: Optional callback for download progress
            
        Returns:
            Path to downloaded file or None if failed
        """
        try:
            url = f"{self.DOWNLOAD_URL}/{identifier}/{filename}"
            file_path = download_path / filename
            
            # Create directory if it doesn't exist
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            logger.info(f"⬇️ Downloading {filename} from {identifier}")
            
            async with self.session.get(url) as response:
                if response.status == 200:
                    total_size = int(response.headers.get('content-length', 0))
                    downloaded = 0
                    
                    with open(file_path, 'wb') as f:
                        async for chunk in response.content.iter_chunked(8192):
                            f.write(chunk)
                            downloaded += len(chunk)
                            
                            if progress_callback and total_size > 0:
                                progress = (downloaded / total_size) * 100
                                await progress_callback(progress, downloaded, total_size)
                    
                    logger.info(f"✅ Downloaded {filename} ({downloaded} bytes)")
                    return file_path
                else:
                    logger.error(f"❌ Failed to download {filename}: {response.status}")
                    return None
                    
        except Exception as e:
            logger.error(f"❌ Error downloading {filename}: {e}")
            return None
    
    async def import_vedic_collection(
        self,
        query: str = "vedic OR sanskrit OR hinduism OR upanishad OR purana",
        max_items: int = 10,
        download_path: Optional[Path] = None
    ) -> List[Dict[str, Any]]:
        """
        Import a collection of Vedic texts from Archive.org
        
        Args:
            query: Search query for Vedic texts
            max_items: Maximum number of items to import
            download_path: Path to download files (optional)
            
        Returns:
            List of imported item information
        """
        try:
            logger.info(f"🚀 Starting Vedic collection import: {query}")
            
            # Search for relevant texts
            search_results = await self.search_vedic_texts(
                query=query,
                limit=max_items
            )
            
            imported_items = []
            
            for item in search_results:
                identifier = item.get("identifier")
                if not identifier:
                    continue
                
                logger.info(f"📖 Processing item: {identifier}")
                
                # Get detailed metadata
                metadata = await self.get_item_metadata(identifier)
                if not metadata:
                    continue
                
                # List available files
                files = await self.list_item_files(identifier)
                
                item_info = {
                    "identifier": identifier,
                    "title": item.get("title", "Unknown"),
                    "creator": item.get("creator", "Unknown"),
                    "description": item.get("description", ""),
                    "date": item.get("date", ""),
                    "language": item.get("language", []),
                    "subject": item.get("subject", []),
                    "downloads": item.get("downloads", 0),
                    "files": files,
                    "metadata": metadata,
                    "imported_at": datetime.utcnow().isoformat()
                }
                
                # Download files if path provided
                if download_path and files:
                    item_info["downloaded_files"] = []
                    for file_info in files[:3]:  # Limit to first 3 files for MVP
                        filename = file_info.get("name")
                        if filename:
                            downloaded_path = await self.download_file(
                                identifier, filename, download_path / identifier
                            )
                            if downloaded_path:
                                item_info["downloaded_files"].append(str(downloaded_path))
                
                imported_items.append(item_info)
                
                # Add delay to be respectful to Archive.org
                await asyncio.sleep(1)
            
            logger.info(f"✅ Imported {len(imported_items)} Vedic texts from Archive.org")
            return imported_items
            
        except Exception as e:
            logger.error(f"❌ Error importing Vedic collection: {e}")
            return []


# Utility functions for Archive.org integration

def filter_vedic_texts(search_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Filter search results to focus on authentic Vedic texts
    
    Args:
        search_results: Raw search results from Archive.org
        
    Returns:
        Filtered list of Vedic texts
    """
    vedic_keywords = [
        "veda", "vedic", "upanishad", "purana", "mahabharata", "ramayana",
        "bhagavad", "gita", "sanskrit", "dharma", "karma", "yoga",
        "brahman", "atman", "moksha", "samsara", "mantra", "yantra"
    ]
    
    filtered_results = []
    
    for item in search_results:
        title = item.get("title", "").lower()
        description = item.get("description", "").lower()
        subject = " ".join(item.get("subject", [])).lower()
        
        # Check if any Vedic keywords are present
        text_content = f"{title} {description} {subject}"
        if any(keyword in text_content for keyword in vedic_keywords):
            filtered_results.append(item)
    
    return filtered_results


def extract_language_info(metadata: Dict[str, Any]) -> List[str]:
    """
    Extract language information from Archive.org metadata
    
    Args:
        metadata: Item metadata from Archive.org
        
    Returns:
        List of detected languages
    """
    languages = []
    
    # Check various metadata fields for language info
    lang_fields = ["language", "lang", "languages"]
    
    for field in lang_fields:
        if field in metadata:
            lang_value = metadata[field]
            if isinstance(lang_value, str):
                languages.append(lang_value)
            elif isinstance(lang_value, list):
                languages.extend(lang_value)
    
    # Deduplicate and normalize
    languages = list(set(lang.strip().lower() for lang in languages if lang))
    
    return languages
