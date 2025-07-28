"""
Vāṇmayam (वाङ्मयम्) - The Vedic Corpus Portal
Main FastAPI application entry point
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import time
import uuid

from app.core.config import settings
from app.core.database import init_db
from app.core.health import wait_for_database
from app.core.logging import setup_logging
from app.api.v1.api import api_router

# Setup logging
logger = setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    logger.info("🕉️  Starting Vāṇmayam - The Vedic Corpus Portal")
    
    # Database integration re-enabled after resolving connection issues
    logger.info("🚀 Database integration enabled - connecting to PostgreSQL")
    
    # Wait for database to be ready
    logger.info("⏳ Waiting for database connection...")
    if not await wait_for_database():
        logger.error("❌ Failed to connect to database after retries")
        raise RuntimeError("Database connection failed")
    
    await init_db()
    logger.info("✅ Database initialized successfully")
    
    yield
    
    # Shutdown
    logger.info("🙏 Shutting down Vāṇmayam gracefully")


# Create FastAPI application
app = FastAPI(
    title="वाङ्मयम् (Vāṇmayam) - The Vedic Corpus Portal",
    description="""
    ## 🕉️ The Vedic Corpus Portal
    
    A digital preservation platform for Vedic literature with AI-powered OCR, 
    collaborative editing, and Sanskrit-optimized search.
    
    ### Features
    - **Multi-engine OCR**: Tesseract + Google Vision API
    - **Collaborative Editing**: Side-by-side proofreading
    - **Sanskrit Search**: Full-text search with Devanagari support
    - **Role-based Access**: Admin, Editor, Reader, Scholar roles
    - **Export Options**: PDF, text, and ePub formats
    
    ### Authentication
    - Google OAuth 2.0 integration
    - JWT token-based sessions
    - Role-based permissions
    
    ---
    **Vaidika Samrakshana Parishad** - Preserving Vedic heritage through technology
    """,
    version="1.0.0-mvp",
    contact={
        "name": "Vaidika Samrakshana Parishad",
        "email": "admin@vangmayam.org",
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT",
    },
    lifespan=lifespan,
)

# Security middleware
app.add_middleware(
    TrustedHostMiddleware, 
    allowed_hosts=settings.ALLOWED_HOSTS
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Add processing time and request ID headers"""
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    
    response.headers["X-Process-Time"] = str(process_time)
    response.headers["X-Request-ID"] = request_id
    
    return response


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler"""
    request_id = getattr(request.state, 'request_id', 'unknown')
    logger.error(f"Unhandled exception in request {request_id}: {exc}")
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "request_id": request_id,
            "message": "An unexpected error occurred. Please try again later."
        }
    )


# Health check endpoint
@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "vangmayam-api",
        "version": "1.0.0-mvp",
        "timestamp": time.time()
    }


# Root endpoint
@app.get("/", tags=["Root"])
async def root():
    """Root endpoint with Sanskrit greeting"""
    return {
        "message": "🕉️ स्वागतम् (Svāgatam) - Welcome to Vāṇmayam",
        "description": "The Vedic Corpus Portal - Preserving ancient wisdom through modern technology",
        "docs": "/docs",
        "health": "/health"
    }


# Include API routes
app.include_router(api_router, prefix="/api/v1")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
