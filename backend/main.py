from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager
import logging
import os

from config import get_settings
from db.database import engine
from db.models import Base
from api import upload, readings, devices

# Configure logging
settings = get_settings()
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting WattBox API...")
    
    # Create database tables
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created/verified")
    
    # Ensure upload directories exist
    for subdir in ['raw', 'processed', 'failed']:
        os.makedirs(os.path.join(settings.UPLOAD_DIRECTORY, subdir), exist_ok=True)
    
    yield
    
    # Shutdown
    logger.info("Shutting down WattBox API...")

# Create FastAPI app
app = FastAPI(
    title=settings.API_TITLE,
    version=settings.API_VERSION,
    lifespan=lifespan
)

# Configure CORS
origins = settings.CORS_ORIGINS.split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(upload.router)
app.include_router(readings.router)
app.include_router(devices.router)

# Serve static files (images)
app.mount("/images", StaticFiles(directory=settings.UPLOAD_DIRECTORY), name="images")

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": settings.API_TITLE,
        "version": settings.API_VERSION,
        "status": "operational",
        "endpoints": {
            "upload": "/upload",
            "readings": "/readings",
            "devices": "/devices",
            "docs": "/docs"
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": settings.API_TITLE,
        "version": settings.API_VERSION
    }

# Rate limiting middleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Apply rate limiting to upload endpoints
@app.post("/upload/device")
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute")
async def rate_limited_device_upload(request: Request):
    pass

@app.post("/upload/manual")
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute")
async def rate_limited_manual_upload(request: Request):
    pass

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=True
    )