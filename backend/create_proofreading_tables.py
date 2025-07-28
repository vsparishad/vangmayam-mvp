#!/usr/bin/env python3
"""
Database Migration Script for Proofreading Tables

This script creates all the necessary tables for the collaborative proofreading
and editorial workflow system in the Vāṇmayam database.

Tables created:
- proofreading_tasks
- proofreading_edits  
- proofreading_comments
- proofreading_sessions
- sanskrit_glossary
- proofreading_quality_metrics
"""

import asyncio
import logging
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.core.database import Base
from app.models.proofreading import (
    ProofreadingTask, ProofreadingEdit, ProofreadingComment,
    ProofreadingSession, SanskritGlossaryEntry, ProofreadingQualityMetrics
)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def create_proofreading_tables():
    """
    Create all proofreading-related database tables
    """
    try:
        logger.info("🚀 Starting proofreading tables creation...")
        
        # Create async engine
        engine = create_async_engine(
            settings.DATABASE_URL,
            echo=True,  # Show SQL statements
            future=True
        )
        
        # Create all tables
        async with engine.begin() as conn:
            logger.info("📋 Creating proofreading tables...")
            
            # Import all models to ensure they're registered
            from app.models import user, book, proofreading
            
            # Create tables
            await conn.run_sync(Base.metadata.create_all)
            
            logger.info("✅ All proofreading tables created successfully!")
        
        # Test table creation by checking if tables exist
        async_session = sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )
        
        async with async_session() as session:
            # Test each table by running a simple count query
            from sqlalchemy import text
            
            tables_to_test = [
                "proofreading_tasks",
                "proofreading_edits", 
                "proofreading_comments",
                "proofreading_sessions",
                "sanskrit_glossary",
                "proofreading_quality_metrics"
            ]
            
            logger.info("🧪 Testing table creation...")
            for table in tables_to_test:
                try:
                    result = await session.execute(text(f"SELECT COUNT(*) FROM {table}"))
                    count = result.scalar()
                    logger.info(f"✅ Table '{table}': {count} rows")
                except Exception as e:
                    logger.error(f"❌ Table '{table}' test failed: {e}")
                    raise
        
        await engine.dispose()
        logger.info("🎉 Proofreading database migration completed successfully!")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error creating proofreading tables: {e}")
        raise


async def add_sample_glossary_entries():
    """
    Add some sample Sanskrit glossary entries for testing
    """
    try:
        logger.info("📚 Adding sample Sanskrit glossary entries...")
        
        engine = create_async_engine(settings.DATABASE_URL, future=True)
        async_session = sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )
        
        async with async_session() as session:
            # Sample Sanskrit words
            sample_entries = [
                {
                    "word_devanagari": "वेद",
                    "word_iast": "veda",
                    "word_romanized": "veda",
                    "part_of_speech": "noun",
                    "gender": "masculine",
                    "meaning_english": "knowledge, sacred knowledge, Vedic text",
                    "meaning_hindi": "ज्ञान, पवित्र ज्ञान, वैदिक ग्रंथ",
                    "context": "vedic",
                    "source": "system",
                    "is_verified": True,
                    "frequency": 100
                },
                {
                    "word_devanagari": "मन्त्र",
                    "word_iast": "mantra",
                    "word_romanized": "mantra", 
                    "part_of_speech": "noun",
                    "gender": "masculine",
                    "meaning_english": "sacred utterance, hymn, incantation",
                    "meaning_hindi": "पवित्र उच्चारण, स्तुति, मंत्र",
                    "context": "vedic",
                    "source": "system",
                    "is_verified": True,
                    "frequency": 95
                },
                {
                    "word_devanagari": "ब्राह्मण",
                    "word_iast": "brāhmaṇa",
                    "word_romanized": "brahmana",
                    "part_of_speech": "noun", 
                    "gender": "masculine",
                    "meaning_english": "Brahmin, priestly class, Brahmana text",
                    "meaning_hindi": "ब्राह्मण, पुरोहित वर्ग, ब्राह्मण ग्रंथ",
                    "context": "vedic",
                    "source": "system",
                    "is_verified": True,
                    "frequency": 80
                },
                {
                    "word_devanagari": "यज्ञ",
                    "word_iast": "yajña",
                    "word_romanized": "yajna",
                    "part_of_speech": "noun",
                    "gender": "masculine", 
                    "meaning_english": "sacrifice, ritual offering, worship",
                    "meaning_hindi": "यज्ञ, बलिदान, पूजा",
                    "context": "vedic",
                    "source": "system",
                    "is_verified": True,
                    "frequency": 90
                },
                {
                    "word_devanagari": "ऋषि",
                    "word_iast": "ṛṣi",
                    "word_romanized": "rishi",
                    "part_of_speech": "noun",
                    "gender": "masculine",
                    "meaning_english": "sage, seer, Vedic poet",
                    "meaning_hindi": "ऋषि, द्रष्टा, वैदिक कवि", 
                    "context": "vedic",
                    "source": "system",
                    "is_verified": True,
                    "frequency": 75
                }
            ]
            
            # Add entries to database
            for entry_data in sample_entries:
                entry = SanskritGlossaryEntry(**entry_data)
                session.add(entry)
            
            await session.commit()
            logger.info(f"✅ Added {len(sample_entries)} sample glossary entries")
        
        await engine.dispose()
        
    except Exception as e:
        logger.error(f"❌ Error adding sample glossary entries: {e}")
        raise


async def main():
    """
    Main migration function
    """
    try:
        logger.info("🎯 Starting Vāṇmayam proofreading database migration...")
        
        # Create tables
        await create_proofreading_tables()
        
        # Add sample data
        await add_sample_glossary_entries()
        
        logger.info("🎉 Migration completed successfully!")
        logger.info("📋 Next steps:")
        logger.info("   1. Test proofreading API endpoints")
        logger.info("   2. Create sample proofreading tasks")
        logger.info("   3. Test collaborative editing workflows")
        
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        return False
    
    return True


if __name__ == "__main__":
    # Run the migration
    success = asyncio.run(main())
    if success:
        print("\n✅ Proofreading database migration completed successfully!")
    else:
        print("\n❌ Migration failed. Check logs for details.")
        exit(1)
