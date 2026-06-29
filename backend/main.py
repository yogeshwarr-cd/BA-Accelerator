import os
import sys

# Add the framework directory to sys.path to allow importing designlab_core directly
framework_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../framework"))
if framework_path not in sys.path:
    sys.path.insert(0, framework_path)

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.config import settings

# Import database configuration and metadata base
from backend.db.postgres import engine, Base
# Import all database models to register with Base
from backend.db.models import Job, Requirement, Story, AuditLog
from backend.validation_export.db_models import (
    ValidationResultDB, ValidationFindingDB, BAReviewDB,
    AuditEventDB, RevisionPackageDB, ValidatedStoryPackageDB
)

# Import API routes
from backend.api.routes import ingest, pipeline, stories, audit
from backend.validation_export.api import router as validation_router
from backend.api.middleware import RequestLoggingMiddleware
from backend.shared.logger import get_logger

logger = get_logger(__name__)

app = FastAPI(
    title="BA Accelerator API",
    description="AI-Powered Requirement-to-User-Story Generation System",
    version="1.0.0"
)

# CORS Policy configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Custom logging middleware
app.add_middleware(RequestLoggingMiddleware)

# Include API routers
app.include_router(ingest.router)
app.include_router(pipeline.router)
app.include_router(stories.router)
app.include_router(audit.router)
app.include_router(validation_router)

@app.on_event("startup")
async def on_startup():
    """
    FastAPI startup hook. Automatically creates database tables.
    """
    logger.info("Initializing database and compiling schemas...")
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables initialized successfully.")
    except Exception as e:
        logger.critical(f"Failed to initialize database tables: {str(e)}")

@app.get("/", tags=["Root"])
def root():
    return {
        "message": "BA Accelerator API Running",
        "docs": "/docs",
        "health": "/health"
    }

@app.get("/health", tags=["Health"])
async def health_check():
    """
    Liveness probe. Returns current operational status.
    """
    return {"status": "OK", "version": "1.0.0"}

if __name__ == "__main__":
    # Start ASGI server
    uvicorn.run(
        "backend.main:app", 
        host=settings.HOST or "0.0.0.0", 
        port=settings.PORT or 8000, 
        reload=False
    )

# INTEGRATION NOTE
# Uvicorn loads config ports from global settings.
# FastAPI automatic documentation is accessible at /docs or /redoc.
