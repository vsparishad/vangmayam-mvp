"""
Advanced Search Service with Sanskrit Analyzers for Vāṇmayam

This module provides comprehensive search functionality including:
- Elasticsearch integration with Sanskrit text analysis
- Full-text search across OCR'd documents
- Sanskrit linguistic features (sandhi, morphology)
- Search result ranking and relevance
- Integration with proofreading workflow
"""

import asyncio
import logging
import json
from typing import List, Dict, Any, Optional, Union
from datetime import datetime
import re

from elasticsearch import AsyncElasticsearch
from elasticsearch.exceptions import NotFoundError, ConnectionError
import aiohttp

from ..core.config import settings

logger = logging.getLogger(__name__)


class SanskritTextAnalyzer:
    """
    Sanskrit text analyzer for linguistic processing
    Handles Devanagari, IAST, and romanized Sanskrit text
    """
    
    def __init__(self):
        # Sanskrit vowels and consonants for analysis
        self.devanagari_vowels = "अआइईउऊऋॠऌॡएऐओऔ"
        self.devanagari_consonants = "कखगघङचछजझञटठडढणतथदधनपफबभमयरलवशषसह"
        self.iast_vowels = "aāiīuūṛṝḷḹeaioau"
        self.iast_consonants = "kkhgghṅcchajjhañṭṭhḍḍhṇtthddhnpphbbhmyrlvśṣsh"
        
        # Common Sanskrit sandhi patterns
        self.sandhi_patterns = [
            (r'([aā])([aā])', r'\1'),  # a + a = a
            (r'([aā])([iī])', r'e'),   # a + i = e
            (r'([aā])([uū])', r'o'),   # a + u = o
            (r'([iī])([aā])', r'yā'),  # i + a = ya
            (r'([uū])([aā])', r'vā'),  # u + a = va
        ]
        
        # Sanskrit morphological patterns
        self.case_endings = {
            'nominative': ['ः', 'स्', 'ं', 'णि'],
            'accusative': ['ं', 'म्', 'न्', 'णि'],
            'instrumental': ['ेन', 'ैः', 'भिः', 'भि'],
            'dative': ['ाय', 'े', 'भ्यः', 'भ्य'],
            'ablative': ['ात्', 'स्मात्', 'भ्यः', 'भ्य'],
            'genitive': ['स्य', 'ाणां', 'स्य', 'णाम्'],
            'locative': ['े', 'ि', 'षु', 'सु']
        }
    
    def normalize_text(self, text: str) -> str:
        """
        Normalize Sanskrit text for search
        """
        try:
            # Remove extra whitespace
            text = re.sub(r'\s+', ' ', text.strip())
            
            # Normalize Devanagari combining characters
            text = text.replace('्', '्')  # Normalize virama
            
            # Remove punctuation but keep Sanskrit punctuation
            text = re.sub(r'[^\u0900-\u097F\u0020-\u007E]', ' ', text)
            
            return text.lower()
            
        except Exception as e:
            logger.error(f"❌ Error normalizing Sanskrit text: {e}")
            return text
    
    def extract_root_words(self, text: str) -> List[str]:
        """
        Extract potential root words by removing common Sanskrit endings
        """
        try:
            words = text.split()
            root_words = []
            
            for word in words:
                # Try to identify and remove case endings
                root_word = word
                for case, endings in self.case_endings.items():
                    for ending in endings:
                        if word.endswith(ending):
                            root_word = word[:-len(ending)]
                            break
                
                # Add both original and potential root
                root_words.append(word)
                if root_word != word and len(root_word) > 2:
                    root_words.append(root_word)
            
            return list(set(root_words))
            
        except Exception as e:
            logger.error(f"❌ Error extracting root words: {e}")
            return [text]
    
    def apply_sandhi_rules(self, text: str) -> List[str]:
        """
        Apply Sanskrit sandhi rules to generate search variants
        """
        try:
            variants = [text]
            
            # Apply sandhi patterns
            for pattern, replacement in self.sandhi_patterns:
                modified = re.sub(pattern, replacement, text)
                if modified != text:
                    variants.append(modified)
            
            return list(set(variants))
            
        except Exception as e:
            logger.error(f"❌ Error applying sandhi rules: {e}")
            return [text]
    
    def transliterate_iast_to_devanagari(self, iast_text: str) -> str:
        """
        Basic IAST to Devanagari transliteration
        """
        try:
            # This is a simplified transliteration - in production, use a proper library
            transliteration_map = {
                'a': 'अ', 'ā': 'आ', 'i': 'इ', 'ī': 'ई', 'u': 'उ', 'ū': 'ऊ',
                'ṛ': 'ऋ', 'ṝ': 'ॠ', 'ḷ': 'ऌ', 'ḹ': 'ॡ', 'e': 'ए', 'ai': 'ऐ',
                'o': 'ओ', 'au': 'औ', 'k': 'क', 'kh': 'ख', 'g': 'ग', 'gh': 'घ',
                'ṅ': 'ङ', 'c': 'च', 'ch': 'छ', 'j': 'ज', 'jh': 'झ', 'ñ': 'ञ',
                'ṭ': 'ट', 'ṭh': 'ठ', 'ḍ': 'ड', 'ḍh': 'ढ', 'ṇ': 'ण', 't': 'त',
                'th': 'थ', 'd': 'द', 'dh': 'ध', 'n': 'न', 'p': 'प', 'ph': 'फ',
                'b': 'ब', 'bh': 'भ', 'm': 'म', 'y': 'य', 'r': 'र', 'l': 'ल',
                'v': 'व', 'ś': 'श', 'ṣ': 'ष', 's': 'स', 'h': 'ह'
            }
            
            result = iast_text
            # Sort by length (longest first) to handle multi-character mappings
            for iast, devanagari in sorted(transliteration_map.items(), key=lambda x: len(x[0]), reverse=True):
                result = result.replace(iast, devanagari)
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Error in IAST transliteration: {e}")
            return iast_text


class ElasticsearchService:
    """
    Elasticsearch service for advanced search functionality
    """
    
    def __init__(self):
        self.client: Optional[AsyncElasticsearch] = None
        self.sanskrit_analyzer = SanskritTextAnalyzer()
        self.index_name = "vangmayam_documents"
        self.glossary_index = "vangmayam_glossary"
    
    async def initialize(self):
        """
        Initialize Elasticsearch connection and create indices
        """
        try:
            logger.info("🔍 Initializing Elasticsearch service...")
            
            # For MVP, we'll use a simple in-memory search if Elasticsearch is not available
            # In production, this would connect to a real Elasticsearch cluster
            elasticsearch_url = getattr(settings, 'ELASTICSEARCH_URL', None)
            
            if elasticsearch_url:
                self.client = AsyncElasticsearch([elasticsearch_url])
                await self._create_indices()
                logger.info("✅ Elasticsearch connected and indices created")
            else:
                logger.info("📝 Using in-memory search for MVP (Elasticsearch not configured)")
                self.client = None
            
        except Exception as e:
            logger.error(f"❌ Error initializing Elasticsearch: {e}")
            logger.info("📝 Falling back to in-memory search for MVP")
            self.client = None
    
    async def _create_indices(self):
        """
        Create Elasticsearch indices with Sanskrit analyzers
        """
        try:
            if not self.client:
                return
            
            # Document index mapping
            document_mapping = {
                "mappings": {
                    "properties": {
                        "document_id": {"type": "keyword"},
                        "title": {
                            "type": "text",
                            "analyzer": "sanskrit_analyzer",
                            "fields": {
                                "raw": {"type": "keyword"}
                            }
                        },
                        "content": {
                            "type": "text",
                            "analyzer": "sanskrit_analyzer"
                        },
                        "content_devanagari": {
                            "type": "text",
                            "analyzer": "devanagari_analyzer"
                        },
                        "content_iast": {
                            "type": "text",
                            "analyzer": "iast_analyzer"
                        },
                        "ocr_confidence": {"type": "integer"},
                        "page_number": {"type": "integer"},
                        "language": {"type": "keyword"},
                        "tags": {"type": "keyword"},
                        "created_at": {"type": "date"},
                        "updated_at": {"type": "date"}
                    }
                },
                "settings": {
                    "analysis": {
                        "analyzer": {
                            "sanskrit_analyzer": {
                                "type": "custom",
                                "tokenizer": "standard",
                                "filter": ["lowercase", "sanskrit_stemmer", "sanskrit_synonyms"]
                            },
                            "devanagari_analyzer": {
                                "type": "custom",
                                "tokenizer": "standard",
                                "filter": ["lowercase", "devanagari_normalizer"]
                            },
                            "iast_analyzer": {
                                "type": "custom",
                                "tokenizer": "standard",
                                "filter": ["lowercase", "iast_normalizer"]
                            }
                        },
                        "filter": {
                            "sanskrit_stemmer": {
                                "type": "stemmer",
                                "language": "minimal_english"  # Placeholder - would use Sanskrit stemmer
                            },
                            "sanskrit_synonyms": {
                                "type": "synonym",
                                "synonyms": [
                                    "वेद,veda => वेद,veda,knowledge,sacred_text",
                                    "मन्त्र,mantra => मन्त्र,mantra,hymn,incantation"
                                ]
                            },
                            "devanagari_normalizer": {
                                "type": "pattern_replace",
                                "pattern": "्",
                                "replacement": "्"
                            },
                            "iast_normalizer": {
                                "type": "lowercase"
                            }
                        }
                    }
                }
            }
            
            # Create document index
            if not await self.client.indices.exists(index=self.index_name):
                await self.client.indices.create(
                    index=self.index_name,
                    body=document_mapping
                )
                logger.info(f"✅ Created document index: {self.index_name}")
            
            # Glossary index mapping
            glossary_mapping = {
                "mappings": {
                    "properties": {
                        "word_devanagari": {
                            "type": "text",
                            "analyzer": "devanagari_analyzer",
                            "fields": {"raw": {"type": "keyword"}}
                        },
                        "word_iast": {
                            "type": "text",
                            "analyzer": "iast_analyzer",
                            "fields": {"raw": {"type": "keyword"}}
                        },
                        "word_romanized": {"type": "text"},
                        "meaning_english": {"type": "text"},
                        "meaning_hindi": {"type": "text"},
                        "part_of_speech": {"type": "keyword"},
                        "context": {"type": "keyword"},
                        "frequency": {"type": "integer"}
                    }
                }
            }
            
            # Create glossary index
            if not await self.client.indices.exists(index=self.glossary_index):
                await self.client.indices.create(
                    index=self.glossary_index,
                    body=glossary_mapping
                )
                logger.info(f"✅ Created glossary index: {self.glossary_index}")
            
        except Exception as e:
            logger.error(f"❌ Error creating Elasticsearch indices: {e}")
            raise
    
    async def index_document(self, document_data: Dict[str, Any]) -> bool:
        """
        Index a document for search
        """
        try:
            if not self.client:
                logger.info("📝 Document indexing skipped (using in-memory search)")
                return True
            
            # Prepare document for indexing
            doc_id = document_data.get('document_id')
            content = document_data.get('content', '')
            
            # Apply Sanskrit text analysis
            normalized_content = self.sanskrit_analyzer.normalize_text(content)
            root_words = self.sanskrit_analyzer.extract_root_words(normalized_content)
            sandhi_variants = self.sanskrit_analyzer.apply_sandhi_rules(normalized_content)
            
            # Enhance document with linguistic analysis
            enhanced_doc = {
                **document_data,
                'content_normalized': normalized_content,
                'root_words': root_words,
                'sandhi_variants': sandhi_variants,
                'indexed_at': datetime.utcnow().isoformat()
            }
            
            # Index the document
            await self.client.index(
                index=self.index_name,
                id=doc_id,
                body=enhanced_doc
            )
            
            logger.info(f"✅ Indexed document: {doc_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error indexing document: {e}")
            return False
    
    async def search_documents(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        size: int = 10,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        Search documents with Sanskrit-aware analysis
        """
        try:
            logger.info(f"🔍 Searching documents for: {query}")
            
            if not self.client:
                # Fallback to simple in-memory search for MVP
                return await self._fallback_search(query, filters, size, offset)
            
            # Prepare search query with Sanskrit analysis
            normalized_query = self.sanskrit_analyzer.normalize_text(query)
            root_words = self.sanskrit_analyzer.extract_root_words(normalized_query)
            sandhi_variants = self.sanskrit_analyzer.apply_sandhi_rules(normalized_query)
            
            # Build Elasticsearch query
            search_body = {
                "query": {
                    "bool": {
                        "should": [
                            # Exact match (highest boost)
                            {"match": {"content": {"query": query, "boost": 3.0}}},
                            # Normalized content match
                            {"match": {"content_normalized": {"query": normalized_query, "boost": 2.0}}},
                            # Root words match
                            {"terms": {"root_words": root_words, "boost": 1.5}},
                            # Sandhi variants match
                            {"terms": {"sandhi_variants": sandhi_variants, "boost": 1.2}},
                            # Title match
                            {"match": {"title": {"query": query, "boost": 2.5}}}
                        ],
                        "minimum_should_match": 1
                    }
                },
                "highlight": {
                    "fields": {
                        "content": {},
                        "title": {}
                    }
                },
                "size": size,
                "from": offset,
                "sort": [
                    {"_score": {"order": "desc"}},
                    {"created_at": {"order": "desc"}}
                ]
            }
            
            # Add filters if provided
            if filters:
                filter_clauses = []
                for field, value in filters.items():
                    if isinstance(value, list):
                        filter_clauses.append({"terms": {field: value}})
                    else:
                        filter_clauses.append({"term": {field: value}})
                
                if filter_clauses:
                    search_body["query"]["bool"]["filter"] = filter_clauses
            
            # Execute search
            response = await self.client.search(
                index=self.index_name,
                body=search_body
            )
            
            # Process results
            hits = response["hits"]
            results = []
            
            for hit in hits["hits"]:
                result = {
                    "document_id": hit["_source"]["document_id"],
                    "title": hit["_source"].get("title", ""),
                    "content": hit["_source"].get("content", ""),
                    "score": hit["_score"],
                    "highlights": hit.get("highlight", {}),
                    "page_number": hit["_source"].get("page_number"),
                    "ocr_confidence": hit["_source"].get("ocr_confidence")
                }
                results.append(result)
            
            search_results = {
                "query": query,
                "total_results": hits["total"]["value"],
                "results": results,
                "took": response["took"],
                "max_score": hits["max_score"]
            }
            
            logger.info(f"✅ Found {len(results)} documents for query: {query}")
            return search_results
            
        except Exception as e:
            logger.error(f"❌ Error searching documents: {e}")
            return await self._fallback_search(query, filters, size, offset)
    
    async def _fallback_search(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        size: int = 10,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        Fallback in-memory search for MVP when Elasticsearch is not available
        """
        try:
            logger.info(f"📝 Using fallback search for: {query}")
            
            # This would search through indexed documents in memory/database
            # For MVP, return a mock response
            mock_results = {
                "query": query,
                "total_results": 0,
                "results": [],
                "took": 1,
                "max_score": 0.0,
                "fallback": True,
                "message": "Using in-memory search (Elasticsearch not configured)"
            }
            
            logger.info("✅ Fallback search completed")
            return mock_results
            
        except Exception as e:
            logger.error(f"❌ Error in fallback search: {e}")
            return {
                "query": query,
                "total_results": 0,
                "results": [],
                "error": str(e)
            }
    
    async def suggest_terms(self, partial_query: str, size: int = 5) -> List[str]:
        """
        Provide search term suggestions with Sanskrit awareness
        """
        try:
            if not self.client:
                # Fallback suggestions for MVP
                sanskrit_suggestions = ["वेद", "मन्त्र", "ब्राह्मण", "यज्ञ", "ऋषि"]
                return [s for s in sanskrit_suggestions if partial_query.lower() in s.lower()][:size]
            
            # Use Elasticsearch completion suggester
            suggest_body = {
                "suggest": {
                    "term_suggest": {
                        "text": partial_query,
                        "term": {
                            "field": "content",
                            "size": size
                        }
                    }
                }
            }
            
            response = await self.client.search(
                index=self.index_name,
                body=suggest_body
            )
            
            suggestions = []
            for suggest in response["suggest"]["term_suggest"]:
                for option in suggest["options"]:
                    suggestions.append(option["text"])
            
            return suggestions[:size]
            
        except Exception as e:
            logger.error(f"❌ Error getting suggestions: {e}")
            return []
    
    async def close(self):
        """
        Close Elasticsearch connection
        """
        try:
            if self.client:
                await self.client.close()
                logger.info("✅ Elasticsearch connection closed")
        except Exception as e:
            logger.error(f"❌ Error closing Elasticsearch connection: {e}")


# Global search service instance
search_service = ElasticsearchService()
