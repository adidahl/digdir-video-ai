"""Main FastAPI application entry point."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.config import get_settings
from app.database import engine, Base
from app.api import auth, videos, search, admin, users, chat
from app.services.lightrag_service import get_lightrag_service, shutdown_lightrag_service
import logging

logger = logging.getLogger(__name__)
settings = get_settings()

# Create database tables
Base.metadata.create_all(bind=engine)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle - startup and shutdown."""
    # Startup
    logger.info("Starting Video RAG Platform...")
    try:
        # Initialize LightRAG service
        lightrag_service = await get_lightrag_service()
        logger.info("LightRAG service initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize LightRAG service: {e}")
        raise
    
    yield  # Application is running
    
    # Shutdown
    logger.info("Shutting down Video RAG Platform...")
    try:
        # Finalize all LightRAG instances
        await shutdown_lightrag_service()
        logger.info("LightRAG service shutdown successfully")
    except Exception as e:
        logger.error(f"Error during LightRAG shutdown: {e}")


app = FastAPI(
    title=settings.app_name,
    description="Video RAG Platform with semantic search and multi-tenant support",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(videos.router, prefix="/api/videos", tags=["Videos"])
app.include_router(search.router, prefix="/api/search", tags=["Search"])
app.include_router(chat.router, prefix="/api/chat", tags=["Chat"])
app.include_router(admin.router, prefix="/api/admin", tags=["Admin"])
app.include_router(users.router, prefix="/api/users", tags=["Users"])


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Video RAG Platform API",
        "version": "1.0.0",
        "docs": "/api/docs"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}

