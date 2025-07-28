"""
Database health check and connection utilities
"""
import asyncio
import asyncpg
from loguru import logger
from app.core.config import settings


async def wait_for_database(max_retries: int = 30, retry_interval: float = 1.0) -> bool:
    """
    Wait for database to become available with retry logic
    
    Args:
        max_retries: Maximum number of connection attempts
        retry_interval: Seconds to wait between attempts
        
    Returns:
        True if database is available, False if max retries exceeded
    """
    for attempt in range(1, max_retries + 1):
        try:
            # Parse database URL to get connection parameters
            db_url = str(settings.DATABASE_URL)
            if db_url.startswith("postgresql+asyncpg://"):
                db_url = db_url.replace("postgresql+asyncpg://", "postgresql://")
            
            # Test connection with explicit parameters for containerized DB
            conn = await asyncpg.connect(
                host="localhost",
                port=5432,
                user="postgres",
                password="postgres",
                database="vangmayam"
            )
            await conn.execute("SELECT 1")
            await conn.close()
            
            logger.info(f"Database connection successful on attempt {attempt}")
            return True
            
        except Exception as e:
            logger.warning(
                f"Database connection attempt {attempt}/{max_retries} failed: {e}"
            )
            if attempt < max_retries:
                await asyncio.sleep(retry_interval)
            else:
                logger.error(f"Database connection failed after {max_retries} attempts")
                return False
    
    return False


async def check_database_health() -> dict:
    """
    Check database health and return status information
    
    Returns:
        Dictionary with health status and metadata
    """
    try:
        # Use explicit connection parameters for containerized DB
        conn = await asyncpg.connect(
            host="localhost",
            port=5432,
            user="postgres",
            password="postgres",
            database="vangmayam"
        )
        
        # Check basic connectivity
        result = await conn.fetchrow("SELECT current_user, current_database(), version()")
        
        # Check if tables exist
        tables_result = await conn.fetch("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
        """)
        
        await conn.close()
        
        return {
            "status": "healthy",
            "user": result["current_user"],
            "database": result["current_database"],
            "version": result["version"],
            "tables_count": len(tables_result),
            "tables": [row["table_name"] for row in tables_result]
        }
        
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }
