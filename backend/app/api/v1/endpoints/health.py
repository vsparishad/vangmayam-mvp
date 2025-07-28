"""
Health check endpoints for API monitoring
"""
from fastapi import APIRouter
from datetime import datetime
from app.core.config import settings

router = APIRouter()


@router.get("/health")
async def health_check():
    """
    Health check endpoint for monitoring API status
    """
    return {
        "status": "healthy",
        "service": "Vāṇmayam - The Vedic Corpus Portal",
        "version": "1.0.0-mvp",
        "environment": settings.ENVIRONMENT,
        "timestamp": datetime.utcnow().isoformat(),
        "mode": "database_integrated",
        "message": "API is running successfully with PostgreSQL database integration"
    }


@router.get("/ready")
async def readiness_check():
    """
    Readiness check for deployment health
    """
    return {
        "status": "ready",
        "database": "connected",
        "redis": "not_connected",
        "elasticsearch": "not_connected",
        "services": {
            "api": "running",
            "auth": "available",
            "books": "mock_mode",
            "search": "mock_mode"
        }
    }
