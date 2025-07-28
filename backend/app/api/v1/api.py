"""
Main API router for Vāṇmayam v1
"""

from fastapi import APIRouter

from app.api.v1.endpoints import auth, books, users, tags, glossary, search, health, import_pipeline, proofreading, admin

api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(books.router, prefix="/books", tags=["books"])
api_router.include_router(tags.router, prefix="/tags", tags=["tags"])
api_router.include_router(glossary.router, prefix="/glossary", tags=["glossary"])
api_router.include_router(search.router, prefix="/search", tags=["search"])
api_router.include_router(import_pipeline.router, prefix="/import", tags=["import-pipeline"])
api_router.include_router(proofreading.router, prefix="/proofreading", tags=["proofreading"])
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
