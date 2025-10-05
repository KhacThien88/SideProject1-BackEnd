from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging
import time

from app.core.config import settings
from app.api.v1 import auth, upload, textract, cv_storage, admin, cv_admin
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
    title="CV Management & Analysis API",
    description="""
    ## 🎯 Hệ thống Quản lý và Phân tích CV Chuyên nghiệp

    API toàn diện cho việc quản lý, phân tích và tìm kiếm CV với các tính năng:

    ### 🔑 Tính năng chính:
    - **Xác thực & Phân quyền**: Đăng ký, đăng nhập, quản lý token JWT
    - **Upload CV**: Tải lên CV với nhiều định dạng (PDF, DOC, images)
    - **Trích xuất văn bản**: Sử dụng AWS Textract để trích xuất nội dung
    - **Phân tích CV**: AI-powered analysis và structured data extraction
    - **Tìm kiếm thông minh**: Tìm kiếm CV theo kỹ năng, kinh nghiệm
    - **Quản trị hệ thống**: Công cụ quản lý dành cho admin

    ### 🔐 Xác thực:
    - **Bearer Token**: Sử dụng JWT token trong header `Authorization: Bearer <token>`
    - **Role-based Access**: Phân quyền user/admin cho các chức năng khác nhau

    ### 📋 Lưu ý quan trọng:
    - Tất cả API yêu cầu xác thực (trừ register/login)
    - File size tối đa: 10MB
    - Supported formats: PDF, DOC, DOCX, PNG, JPG, JPEG
    - Rate limiting: 100 requests/minute per IP

    ### 🏗️ Kiến trúc:
    - **Database**: PostgreSQL với SQLAlchemy ORM
    - **Storage**: AWS S3 cho file storage
    - **AI Services**: AWS Textract + Custom ML models
    - **Cache**: Redis cho session management
    """,
    version="2.0.0",
    contact={
        "name": "CV Management Team",
        "email": "support@cvmanagement.com",
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT",
    },
    servers=[
        {
            "url": "http://localhost:8000",
            "description": "Development server"
        },
        {
            "url": "https://api.cvmanagement.com",
            "description": "Production server"
        }
    ],
    debug=settings.debug,
    lifespan=lifespan,
    openapi_tags=[
        {
            "name": "Health Check",
            "description": "🏥 **Kiểm tra sức khỏe hệ thống**\n\nEndpoints để kiểm tra trạng thái hoạt động của API và các dịch vụ liên quan."
        },
        {
            "name": "Authentication", 
            "description": "🔐 **Xác thực và quản lý người dùng**\n\nĐăng ký, đăng nhập, đăng xuất, làm mới token, xác thực OTP, quên mật khẩu và cập nhật thông tin cá nhân."
        },
        {
            "name": "File Upload",
            "description": "📁 **Tải lên và quản lý CV**\n\nUpload CV files, kiểm tra trạng thái upload, xóa files và lấy danh sách CV của người dùng."
        },
        {
            "name": "Text Extraction",
            "description": "📄 **Trích xuất văn bản từ CV**\n\nSử dụng AWS Textract để trích xuất và phân tích nội dung văn bản từ CV documents (PDF, DOC, images)."
        },
        {
            "name": "CV Analysis",
            "description": "🔍 **Phân tích và tìm kiếm CV**\n\nPhân tích nội dung CV, tìm kiếm CV theo tiêu chí, xuất dữ liệu và xem thống kê phân tích."
        },
        {
            "name": "Admin",
            "description": "👑 **Quản trị hệ thống**\n\n**Chỉ dành cho Admin**: Quản lý người dùng, xem danh sách users, xóa tài khoản."
        },
        {
            "name": "Admin CV Management",
            "description": "📋 **Quản lý CV cho Admin**\n\n**Chỉ dành cho Admin**: Xem tất cả CV, download, trích xuất văn bản và xóa CV của bất kỳ người dùng nào."
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


# Include routers theo thứ tự logic
app.include_router(auth.router, prefix="/api/v1")
app.include_router(upload.router, prefix="/api/v1")
app.include_router(textract.router, prefix="/api/v1/textract")
app.include_router(cv_storage.router, prefix="/api/v1")
app.include_router(admin.router, prefix="/api/v1")
app.include_router(cv_admin.router, prefix="/api/v1")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level="info"
    )
