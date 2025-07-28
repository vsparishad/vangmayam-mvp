#!/usr/bin/env python3
"""
Simple script to test database connection with asyncpg
"""
import asyncio
import asyncpg
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def test_connection():
    """Test database connection"""
    try:
        # Get database URL from environment
        db_url = os.getenv("DATABASE_URL", "postgresql://vangmayam:vangmayam_dev@localhost:5432/vangmayam")
        print(f"Testing connection to: {db_url}")
        
        # Remove SQLAlchemy prefix if present
        if db_url.startswith("postgresql+asyncpg://"):
            db_url = db_url.replace("postgresql+asyncpg://", "postgresql://")
            print(f"Converted URL to: {db_url}")
        
        # Test connection with explicit parameters for containerized DB
        print("Attempting to connect with explicit parameters...")
        conn = await asyncpg.connect(
            host="localhost",
            port=5432,
            user="postgres",
            password="postgres",
            database="vangmayam"
        )
        print("✅ Connection successful!")
        
        # Test query
        result = await conn.fetchrow("SELECT current_user, current_database(), version()")
        print(f"User: {result['current_user']}")
        print(f"Database: {result['current_database']}")
        print(f"Version: {result['version'][:50]}...")
        
        await conn.close()
        print("✅ Connection closed successfully")
        
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        print(f"Error type: {type(e).__name__}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_connection())
