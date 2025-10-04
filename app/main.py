from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging
import time

from app.core.config import settings
from app.api.v1 import auth, upload, textract, cv_storage
from app.middleware.logging import LoggingMiddleware
from app.middleware.rate_limit import RateLimitMiddleware

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    logger.info("Starting up AI Resume Analyzer & Job Match API...")
    logger.info(f"Debug mode: {settings.debug}")
    logger.info(f"Database region: {settings.dynamodb_region}")
    
    yield
    
    logger.info("Shutting down AI Resume Analyzer & Job Match API...")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="AI-powered resume analysis and job matching system",
    debug=settings.debug,
    lifespan=lifespan,
    openapi_tags=[
        {
            "name": "Health Check",
            "description": "System health and status endpoints"
        },
        {
            "name": "Authentication", 
            "description": "User authentication, registration, login, logout, password reset"
        },
        {
            "name": "File Upload",
            "description": "CV/Resume file upload and management"
        },
        {
            "name": "CV Analysis",
            "description": "CV analysis, storage, search and analytics"
        },
        {
            "name": "Text Extraction",
            "description": "AWS Textract integration for document text extraction"
        },
        {
            "name": "Job Matching",
            "description": "Job matching and recommendation system"
        }
    ]
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.debug else ["https://yourdomain.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add trusted host middleware
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"] if settings.debug else ["yourdomain.com", "*.yourdomain.com"]
)

# Add rate limiting middleware
app.add_middleware(RateLimitMiddleware)

# Add logging middleware
app.add_middleware(LoggingMiddleware)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "timestamp": time.time()
        }
    )


# Health check endpoint
@app.get("/health", tags=["Health Check"])
async def health_check():
    """System health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "service": "AI Resume Analyzer & Job Match API",
        "version": settings.app_version
    }


# Root endpoint
@app.get("/", tags=["Health Check"])
async def root():
    """Root endpoint with API information"""
    return {
        "message": "AI Resume Analyzer & Job Match API",
        "version": settings.app_version,
        "docs": "/docs",
        "health": "/health"
    }


# Include routers
app.include_router(auth.router, prefix="/api/v1")
app.include_router(upload.router, prefix="/api/v1")
app.include_router(textract.router, prefix="/api/v1/textract")
app.include_router(cv_storage.router, prefix="/api/v1")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level="info"
    )
