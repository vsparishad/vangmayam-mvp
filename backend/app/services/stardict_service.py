"""
StarDict Dictionary Import Service for Vāṇmayam

This module provides comprehensive StarDict dictionary import functionality including:
- StarDict file format parsing (.dict, .idx, .ifo files)
- Bulk import of dictionary entries into Sanskrit glossary
- Validation and deduplication of imported entries
- Integration with existing glossary system
- Administrator tools for dictionary management
"""

import asyncio
import logging
import struct
import gzip
import os
from typing import List, Dict, Any, Optional, Tuple, Union
from datetime import datetime
from pathlib import Path
import re

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from sqlalchemy.dialects.postgresql import insert

from ..models.proofreading import SanskritGlossaryEntry
from ..core.database import get_db

logger = logging.getLogger(__name__)


class StarDictParser:
    """
    StarDict dictionary file parser
    Handles .ifo (info), .idx (index), and .dict (data) files
    """
    
    def __init__(self):
        self.info_data = {}
        self.index_data = []
        self.dict_data = b""
        self.entries = []
    
    def parse_ifo_file(self, ifo_path: str) -> Dict[str, Any]:
        """
        Parse StarDict .ifo (info) file
        Contains metadata about the dictionary
        """
        try:
            logger.info(f"📖 Parsing StarDict .ifo file: {ifo_path}")
            
            info_data = {}
            with open(ifo_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # First line should be StarDict's dict ifo file
            if not lines[0].strip().startswith("StarDict's dict ifo file"):
                raise ValueError("Invalid StarDict .ifo file format")
            
            # Parse key-value pairs
            for line in lines[1:]:
                line = line.strip()
                if '=' in line:
                    key, value = line.split('=', 1)
                    info_data[key] = value
            
            # Validate required fields
            required_fields = ['version', 'bookname', 'wordcount', 'idxfilesize']
            for field in required_fields:
                if field not in info_data:
                    raise ValueError(f"Missing required field in .ifo file: {field}")
            
            # Convert numeric fields
            info_data['wordcount'] = int(info_data['wordcount'])
            info_data['idxfilesize'] = int(info_data['idxfilesize'])
            
            self.info_data = info_data
            logger.info(f"✅ Parsed .ifo file: {info_data['bookname']} ({info_data['wordcount']} words)")
            return info_data
            
        except Exception as e:
            logger.error(f"❌ Error parsing .ifo file: {e}")
            raise
    
    def parse_idx_file(self, idx_path: str) -> List[Tuple[str, int, int]]:
        """
        Parse StarDict .idx (index) file
        Contains word list with offsets and lengths
        """
        try:
            logger.info(f"📇 Parsing StarDict .idx file: {idx_path}")
            
            index_data = []
            
            # Check if file is compressed
            is_compressed = idx_path.endswith('.gz')
            
            if is_compressed:
                with gzip.open(idx_path, 'rb') as f:
                    data = f.read()
            else:
                with open(idx_path, 'rb') as f:
                    data = f.read()
            
            offset = 0
            while offset < len(data):
                # Find null terminator for word
                null_pos = data.find(b'\x00', offset)
                if null_pos == -1:
                    break
                
                # Extract word
                word = data[offset:null_pos].decode('utf-8')
                
                # Extract data offset and size (8 bytes total)
                if null_pos + 8 >= len(data):
                    break
                
                data_offset, data_size = struct.unpack('>II', data[null_pos + 1:null_pos + 9])
                
                index_data.append((word, data_offset, data_size))
                offset = null_pos + 9
            
            self.index_data = index_data
            logger.info(f"✅ Parsed .idx file: {len(index_data)} entries")
            return index_data
            
        except Exception as e:
            logger.error(f"❌ Error parsing .idx file: {e}")
            raise
    
    def parse_dict_file(self, dict_path: str) -> bytes:
        """
        Parse StarDict .dict (data) file
        Contains the actual dictionary definitions
        """
        try:
            logger.info(f"📚 Parsing StarDict .dict file: {dict_path}")
            
            # Check if file is compressed
            is_compressed = dict_path.endswith('.gz')
            
            if is_compressed:
                with gzip.open(dict_path, 'rb') as f:
                    dict_data = f.read()
            else:
                with open(dict_path, 'rb') as f:
                    dict_data = f.read()
            
            self.dict_data = dict_data
            logger.info(f"✅ Parsed .dict file: {len(dict_data)} bytes")
            return dict_data
            
        except Exception as e:
            logger.error(f"❌ Error parsing .dict file: {e}")
            raise
    
    def extract_definitions(self) -> List[Dict[str, Any]]:
        """
        Extract word definitions from parsed StarDict data
        """
        try:
            logger.info("🔍 Extracting definitions from StarDict data")
            
            if not self.index_data or not self.dict_data:
                raise ValueError("Index or dictionary data not loaded")
            
            entries = []
            
            for word, offset, size in self.index_data:
                try:
                    # Extract definition data
                    if offset + size > len(self.dict_data):
                        logger.warning(f"⚠️ Definition data out of bounds for word: {word}")
                        continue
                    
                    definition_data = self.dict_data[offset:offset + size]
                    
                    # Parse definition based on data type
                    definition = self._parse_definition_data(definition_data)
                    
                    # Create entry
                    entry = {
                        'word': word,
                        'definition': definition,
                        'source_dict': self.info_data.get('bookname', 'Unknown'),
                        'raw_data': definition_data
                    }
                    
                    entries.append(entry)
                    
                except Exception as e:
                    logger.warning(f"⚠️ Error processing word '{word}': {e}")
                    continue
            
            self.entries = entries
            logger.info(f"✅ Extracted {len(entries)} definitions")
            return entries
            
        except Exception as e:
            logger.error(f"❌ Error extracting definitions: {e}")
            raise
    
    def _parse_definition_data(self, data: bytes) -> str:
        """
        Parse definition data based on StarDict format
        """
        try:
            # Try to decode as UTF-8 text first
            definition = data.decode('utf-8', errors='ignore')
            
            # Clean up the definition
            definition = definition.strip()
            
            # Remove null bytes and control characters
            definition = re.sub(r'[\x00-\x1f\x7f-\x9f]', ' ', definition)
            
            # Normalize whitespace
            definition = re.sub(r'\s+', ' ', definition)
            
            return definition
            
        except Exception as e:
            logger.warning(f"⚠️ Error parsing definition data: {e}")
            return data.decode('utf-8', errors='replace')
    
    def parse_stardict_files(self, base_path: str) -> List[Dict[str, Any]]:
        """
        Parse complete StarDict dictionary from base path
        Automatically finds .ifo, .idx, and .dict files
        """
        try:
            logger.info(f"📖 Parsing StarDict dictionary from: {base_path}")
            
            base_path = Path(base_path)
            
            # Find dictionary files
            ifo_file = None
            idx_file = None
            dict_file = None
            
            # Look for files with same base name
            if base_path.is_file():
                # If a specific file is provided, derive base name
                base_name = base_path.stem
                base_dir = base_path.parent
            else:
                # If directory is provided, look for .ifo file
                base_dir = base_path
                ifo_files = list(base_dir.glob("*.ifo"))
                if not ifo_files:
                    raise ValueError(f"No .ifo file found in directory: {base_dir}")
                base_name = ifo_files[0].stem
            
            # Construct file paths
            ifo_file = base_dir / f"{base_name}.ifo"
            idx_file = base_dir / f"{base_name}.idx"
            dict_file = base_dir / f"{base_name}.dict"
            
            # Check for compressed versions
            if not idx_file.exists():
                idx_file = base_dir / f"{base_name}.idx.gz"
            if not dict_file.exists():
                dict_file = base_dir / f"{base_name}.dict.gz"
            
            # Validate files exist
            if not ifo_file.exists():
                raise FileNotFoundError(f"StarDict .ifo file not found: {ifo_file}")
            if not idx_file.exists():
                raise FileNotFoundError(f"StarDict .idx file not found: {idx_file}")
            if not dict_file.exists():
                raise FileNotFoundError(f"StarDict .dict file not found: {dict_file}")
            
            # Parse files in order
            self.parse_ifo_file(str(ifo_file))
            self.parse_idx_file(str(idx_file))
            self.parse_dict_file(str(dict_file))
            
            # Extract definitions
            entries = self.extract_definitions()
            
            logger.info(f"✅ Successfully parsed StarDict dictionary: {len(entries)} entries")
            return entries
            
        except Exception as e:
            logger.error(f"❌ Error parsing StarDict files: {e}")
            raise


class StarDictImportService:
    """
    Service for importing StarDict dictionaries into Sanskrit glossary
    """
    
    def __init__(self):
        self.parser = StarDictParser()
    
    async def import_stardict_dictionary(
        self,
        dict_path: str,
        db: AsyncSession,
        language: str = "sanskrit",
        context: str = "imported",
        batch_size: int = 100,
        validate_entries: bool = True,
        deduplicate: bool = True
    ) -> Dict[str, Any]:
        """
        Import StarDict dictionary into Sanskrit glossary
        """
        try:
            logger.info(f"📚 Starting StarDict import from: {dict_path}")
            
            # Parse StarDict files
            entries = self.parser.parse_stardict_files(dict_path)
            
            if not entries:
                raise ValueError("No entries found in StarDict dictionary")
            
            # Process entries for import
            processed_entries = []
            skipped_entries = []
            
            for entry in entries:
                try:
                    processed_entry = await self._process_entry_for_import(
                        entry, language, context, validate_entries
                    )
                    if processed_entry:
                        processed_entries.append(processed_entry)
                    else:
                        skipped_entries.append(entry['word'])
                except Exception as e:
                    logger.warning(f"⚠️ Skipping entry '{entry['word']}': {e}")
                    skipped_entries.append(entry['word'])
            
            logger.info(f"📊 Processed {len(processed_entries)} entries, skipped {len(skipped_entries)}")
            
            # Deduplicate if requested
            if deduplicate:
                processed_entries = await self._deduplicate_entries(processed_entries, db)
            
            # Import in batches
            imported_count = 0
            failed_count = 0
            
            for i in range(0, len(processed_entries), batch_size):
                batch = processed_entries[i:i + batch_size]
                try:
                    batch_imported = await self._import_batch(batch, db)
                    imported_count += batch_imported
                    logger.info(f"✅ Imported batch {i//batch_size + 1}: {batch_imported} entries")
                except Exception as e:
                    logger.error(f"❌ Failed to import batch {i//batch_size + 1}: {e}")
                    failed_count += len(batch)
            
            # Prepare import summary
            import_summary = {
                "dictionary_name": self.parser.info_data.get('bookname', 'Unknown'),
                "source_path": dict_path,
                "total_entries": len(entries),
                "processed_entries": len(processed_entries),
                "imported_entries": imported_count,
                "skipped_entries": len(skipped_entries),
                "failed_entries": failed_count,
                "language": language,
                "context": context,
                "import_time": datetime.utcnow().isoformat(),
                "dictionary_info": self.parser.info_data
            }
            
            logger.info(f"🎉 StarDict import completed: {imported_count} entries imported")
            return import_summary
            
        except Exception as e:
            logger.error(f"❌ StarDict import failed: {e}")
            raise
    
    async def _process_entry_for_import(
        self,
        entry: Dict[str, Any],
        language: str,
        context: str,
        validate: bool
    ) -> Optional[Dict[str, Any]]:
        """
        Process a StarDict entry for import into glossary
        """
        try:
            word = entry['word'].strip()
            definition = entry['definition'].strip()
            
            if not word or not definition:
                return None
            
            # Basic validation
            if validate:
                if len(word) > 255 or len(definition) > 10000:
                    logger.warning(f"⚠️ Entry too long, skipping: {word}")
                    return None
            
            # Detect script and extract linguistic information
            word_info = self._analyze_word(word)
            
            # Create glossary entry
            glossary_entry = {
                'word_devanagari': word_info.get('devanagari', word),
                'word_iast': word_info.get('iast', ''),
                'word_romanized': word_info.get('romanized', ''),
                'meaning_english': definition,
                'meaning_hindi': '',  # Could be extracted if available
                'part_of_speech': word_info.get('pos'),
                'gender': word_info.get('gender'),
                'context': context,
                'source': entry.get('source_dict', 'StarDict Import'),
                'frequency': 1,
                'is_verified': False
            }
            
            return glossary_entry
            
        except Exception as e:
            logger.warning(f"⚠️ Error processing entry: {e}")
            return None
    
    def _analyze_word(self, word: str) -> Dict[str, Any]:
        """
        Analyze word to extract linguistic information
        """
        word_info = {}
        
        # Detect script
        if re.search(r'[\u0900-\u097F]', word):
            # Devanagari script
            word_info['devanagari'] = word
            word_info['script'] = 'devanagari'
        elif re.search(r'[āīūṛṝḷḹēōṃḥṅñṭḍṇśṣ]', word):
            # IAST transliteration
            word_info['iast'] = word
            word_info['script'] = 'iast'
        else:
            # Romanized or other
            word_info['romanized'] = word
            word_info['script'] = 'romanized'
        
        # Extract basic grammatical information (simplified)
        word_lower = word.lower()
        
        # Gender detection (basic patterns)
        if word_lower.endswith(('ा', 'a')):
            word_info['gender'] = 'masculine'
        elif word_lower.endswith(('ी', 'ī', 'i')):
            word_info['gender'] = 'feminine'
        elif word_lower.endswith(('म्', 'am', 'um')):
            word_info['gender'] = 'neuter'
        
        return word_info
    
    async def _deduplicate_entries(
        self,
        entries: List[Dict[str, Any]],
        db: AsyncSession
    ) -> List[Dict[str, Any]]:
        """
        Remove duplicate entries based on existing glossary
        """
        try:
            logger.info(f"🔍 Deduplicating {len(entries)} entries")
            
            # Get existing words from database
            existing_words = set()
            
            # Check Devanagari words
            devanagari_words = [e['word_devanagari'] for e in entries if e['word_devanagari']]
            if devanagari_words:
                query = select(SanskritGlossaryEntry.word_devanagari).where(
                    SanskritGlossaryEntry.word_devanagari.in_(devanagari_words)
                )
                result = await db.execute(query)
                existing_words.update(result.scalars().all())
            
            # Check IAST words
            iast_words = [e['word_iast'] for e in entries if e['word_iast']]
            if iast_words:
                query = select(SanskritGlossaryEntry.word_iast).where(
                    SanskritGlossaryEntry.word_iast.in_(iast_words)
                )
                result = await db.execute(query)
                existing_words.update(result.scalars().all())
            
            # Filter out duplicates
            unique_entries = []
            for entry in entries:
                if (entry['word_devanagari'] not in existing_words and 
                    entry['word_iast'] not in existing_words):
                    unique_entries.append(entry)
            
            logger.info(f"✅ Deduplicated: {len(unique_entries)} unique entries")
            return unique_entries
            
        except Exception as e:
            logger.error(f"❌ Error deduplicating entries: {e}")
            return entries
    
    async def _import_batch(
        self,
        entries: List[Dict[str, Any]],
        db: AsyncSession
    ) -> int:
        """
        Import a batch of entries into the database
        """
        try:
            # Prepare entries for bulk insert
            glossary_entries = []
            
            for entry in entries:
                glossary_entry = SanskritGlossaryEntry(**entry)
                glossary_entries.append(glossary_entry)
            
            # Bulk insert
            db.add_all(glossary_entries)
            await db.commit()
            
            return len(glossary_entries)
            
        except Exception as e:
            await db.rollback()
            logger.error(f"❌ Error importing batch: {e}")
            raise
    
    async def list_imported_dictionaries(self, db: AsyncSession) -> List[Dict[str, Any]]:
        """
        List all imported dictionaries with statistics
        """
        try:
            logger.info("📊 Listing imported dictionaries")
            
            # Get dictionary statistics
            from sqlalchemy import func
            query = select(
                SanskritGlossaryEntry.source,
                SanskritGlossaryEntry.context,
                func.count(SanskritGlossaryEntry.id).label('entry_count'),
                func.min(SanskritGlossaryEntry.created_at).label('first_import'),
                func.max(SanskritGlossaryEntry.created_at).label('last_import')
            ).group_by(
                SanskritGlossaryEntry.source,
                SanskritGlossaryEntry.context
            ).order_by(SanskritGlossaryEntry.source)
            
            result = await db.execute(query)
            dictionaries = result.fetchall()
            
            dictionary_list = []
            for dict_info in dictionaries:
                dictionary_list.append({
                    'source': dict_info.source,
                    'context': dict_info.context,
                    'entry_count': dict_info.entry_count,
                    'first_import': dict_info.first_import.isoformat() if dict_info.first_import else None,
                    'last_import': dict_info.last_import.isoformat() if dict_info.last_import else None
                })
            
            logger.info(f"✅ Found {len(dictionary_list)} imported dictionaries")
            return dictionary_list
            
        except Exception as e:
            logger.error(f"❌ Error listing dictionaries: {e}")
            raise


# Global service instance
stardict_service = StarDictImportService()
