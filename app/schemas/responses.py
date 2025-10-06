"""
Common Response Models for API Documentation
Standardized response formats for consistent API documentation
"""

from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field
from datetime import datetime


class BaseResponse(BaseModel):
    """Base response model for all API responses"""
    success: bool = Field(..., description="Indicates if the operation was successful")
    message: str = Field(..., description="Human-readable message about the operation result")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")


class ErrorResponse(BaseModel):
    """Standard error response model"""
    success: bool = Field(False, description="Always false for error responses")
    error: str = Field(..., description="Error type or code")
    detail: str = Field(..., description="Detailed error message")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Error timestamp")
    path: Optional[str] = Field(None, description="API endpoint path where error occurred")


class ValidationErrorResponse(BaseModel):
    """Validation error response model"""
    success: bool = Field(False, description="Always false for validation errors")
    error: str = Field("validation_error", description="Error type")
    detail: str = Field(..., description="Validation error message")
    errors: List[Dict[str, Any]] = Field(..., description="Detailed validation errors")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Error timestamp")


class PaginatedResponse(BaseModel):
    """Paginated response model"""
    success: bool = Field(True, description="Indicates if the operation was successful")
    data: List[Any] = Field(..., description="List of items")
    total: int = Field(..., description="Total number of items")
    page: int = Field(..., description="Current page number")
    per_page: int = Field(..., description="Number of items per page")
    total_pages: int = Field(..., description="Total number of pages")
    has_next: bool = Field(..., description="Whether there is a next page")
    has_prev: bool = Field(..., description="Whether there is a previous page")


class HealthCheckResponse(BaseModel):
    """Health check response model"""
    status: str = Field(..., description="Service status (healthy/unhealthy)")
    timestamp: float = Field(..., description="Unix timestamp of the check")
    service: str = Field(..., description="Service name")
    version: str = Field(..., description="Service version")
    uptime: Optional[float] = Field(None, description="Service uptime in seconds")
    dependencies: Optional[Dict[str, str]] = Field(None, description="Status of external dependencies")


class FileUploadResponse(BaseModel):
    """File upload response model"""
    success: bool = Field(..., description="Indicates if upload was successful")
    message: str = Field(..., description="Upload result message")
    file_id: str = Field(..., description="Unique identifier for the uploaded file")
    file_url: Optional[str] = Field(None, description="URL to access the uploaded file")
    file_size: int = Field(..., description="File size in bytes")
    file_type: str = Field(..., description="File extension/type")
    upload_timestamp: datetime = Field(..., description="When the file was uploaded")
    s3_key: Optional[str] = Field(None, description="S3 storage key for the file")


class FileListResponse(BaseModel):
    """File list response model"""
    success: bool = Field(True, description="Indicates if the operation was successful")
    files: List[Dict[str, Any]] = Field(..., description="List of user's files")
    total_count: int = Field(..., description="Total number of files")
    user_id: str = Field(..., description="User ID who owns the files")


class TextExtractionResponse(BaseModel):
    """Text extraction response model"""
    success: bool = Field(..., description="Indicates if extraction was successful")
    file_id: str = Field(..., description="ID of the processed file")
    text: str = Field(..., description="Extracted text content")
    confidence: float = Field(..., description="Confidence score of the extraction (0-1)")
    word_count: int = Field(..., description="Number of words extracted")
    processing_time: Optional[float] = Field(None, description="Processing time in seconds")
    extraction_timestamp: datetime = Field(..., description="When the extraction was performed")


class CVAnalysisResponse(BaseModel):
    """CV analysis response model"""
    success: bool = Field(..., description="Indicates if analysis was successful")
    file_id: str = Field(..., description="ID of the analyzed file")
    analysis: Dict[str, Any] = Field(..., description="Detailed analysis results")
    skills: List[str] = Field(..., description="Extracted skills")
    experience_years: Optional[int] = Field(None, description="Years of experience")
    education: List[Dict[str, Any]] = Field(..., description="Education information")
    work_experience: List[Dict[str, Any]] = Field(..., description="Work experience")
    confidence_score: float = Field(..., description="Overall confidence score (0-1)")
    analysis_timestamp: datetime = Field(..., description="When the analysis was performed")


class UserResponse(BaseModel):
    """User information response model"""
    success: bool = Field(True, description="Indicates if the operation was successful")
    user: Dict[str, Any] = Field(..., description="User information")
    message: Optional[str] = Field(None, description="Additional message")


class TokenResponse(BaseModel):
    """Authentication token response model"""
    success: bool = Field(True, description="Indicates if authentication was successful")
    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field("bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiration time in seconds")
    user: Dict[str, Any] = Field(..., description="User information")


class AdminUserListResponse(BaseModel):
    """Admin user list response model"""
    success: bool = Field(True, description="Indicates if the operation was successful")
    users: List[Dict[str, Any]] = Field(..., description="List of users")
    total_count: int = Field(..., description="Total number of users")
    page: int = Field(..., description="Current page number")
    per_page: int = Field(..., description="Number of users per page")


class AdminCVListResponse(BaseModel):
    """Admin CV list response model"""
    success: bool = Field(True, description="Indicates if the operation was successful")
    files: List[Dict[str, Any]] = Field(..., description="List of CV files with user info")
    total_count: int = Field(..., description="Total number of CV files")
    message: Optional[str] = Field(None, description="Additional information")


# Simplified HTTP Status Code Examples
HTTP_200_EXAMPLE = {
    "description": "Success",
    "content": {
        "application/json": {
            "example": {
                "success": True,
                "message": "Operation completed successfully"
            }
        }
    }
}

HTTP_400_EXAMPLE = {
    "description": "Bad Request",
    "content": {
        "application/json": {
            "example": {
                "detail": "Invalid input data"
            }
        }
    }
}

HTTP_401_EXAMPLE = {
    "description": "Unauthorized",
    "content": {
        "application/json": {
            "example": {
                "detail": "Invalid or missing authorization token"
            }
        }
    }
}

HTTP_403_EXAMPLE = {
    "description": "Forbidden",
    "content": {
        "application/json": {
            "example": {
                "detail": "Admin access required"
            }
        }
    }
}

HTTP_404_EXAMPLE = {
    "description": "Not Found",
    "content": {
        "application/json": {
            "example": {
                "detail": "Resource not found"
            }
        }
    }
}

HTTP_500_EXAMPLE = {
    "description": "Internal Server Error",
    "content": {
        "application/json": {
            "example": {
                "detail": "An unexpected error occurred"
            }
        }
    }
}
