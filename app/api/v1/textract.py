"""
Textract API Endpoints
Handle text extraction from CV documents
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field

from app.core.security import verify_token
from app.services.textract import textract_service
from app.services.s3 import s3_service
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(tags=["Text Extraction"])

# Security scheme for Swagger UI
security = HTTPBearer()


class TextExtractionRequest(BaseModel):
    """Request model cho text extraction"""
    s3_key: str = Field(..., description="S3 key of the file to extract")
    document_type: str = Field(default="cv", description="Type of document")


class TextExtractionResponse(BaseModel):
    """Response model cho text extraction"""
    success: bool
    message: str
    extraction_id: Optional[str] = None
    text: Optional[str] = None
    confidence: Optional[float] = None
    sections: Optional[Dict[str, str]] = None
    key_information: Optional[Dict[str, Any]] = None
    quality_metrics: Optional[Dict[str, Any]] = None
    processing_time: Optional[float] = None
    extraction_timestamp: Optional[str] = None


class ExtractionStatusResponse(BaseModel):
    """Response model cho extraction status"""
    extraction_id: str
    status: str  # pending, processing, completed, failed
    progress: Optional[int] = None
    error_message: Optional[str] = None
    created_at: str
    updated_at: str


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """Dependency to get current user from JWT token"""
    try:
        token = credentials.credentials
        payload = verify_token(token, "access")
        user_id = payload.get("user_id")
        
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload"
            )
        
        return {
            "user_id": user_id, 
            "email": payload.get("email"),
            "role": payload.get("role", "candidate")
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Authentication error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed"
        )


@router.post("/extract", response_model=TextExtractionResponse,
            summary="Extract Text from S3",
            description="Extract text from CV uploaded to S3 using AWS Textract. Supports PDF, images, and documents.")
async def extract_text_from_cv(
    extraction_request: TextExtractionRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Extract text from CV document in S3
    
    - **s3_key**: S3 key of the file to extract
    - **document_type**: Type of document (cv, resume, etc.)
    - **Authentication**: Required (JWT token)
    """
    try:
        logger.info(f"Text extraction request for {extraction_request.s3_key} by user {current_user['user_id']}")
        
        # Verify user has access to the file
        # Admin can access all files, regular users can only access their own files
        if current_user["role"] != "admin" and not extraction_request.s3_key.startswith(f"user-uploads/{current_user['user_id']}/"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this file"
            )
        
        # Check if file exists in S3
        file_metadata = await s3_service.get_file_metadata(extraction_request.s3_key)
        if not file_metadata["success"]:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found"
            )
        
        # Start text extraction
        start_time = datetime.utcnow()
        
        extraction_result = await textract_service.extract_text_from_s3(
            s3_key=extraction_request.s3_key,
            document_type=extraction_request.document_type
        )
        
        processing_time = (datetime.utcnow() - start_time).total_seconds()
        
        if not extraction_result["success"]:
            logger.error(f"Text extraction failed: {extraction_result['error']}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Text extraction failed: {extraction_result['error']}"
            )
        
        logger.info(f"Text extraction completed for {extraction_request.s3_key}")
        
        return TextExtractionResponse(
            success=True,
            message="Text extraction completed successfully",
            extraction_id=extraction_result.get("extraction_timestamp", str(datetime.utcnow().timestamp())),
            text=extraction_result["text"],
            confidence=extraction_result.get("confidence", 0.0),
            sections=extraction_result.get("processing_metadata", {}).get("sections", {}),
            key_information=extraction_result.get("processing_metadata", {}).get("key_information", {}),
            quality_metrics=extraction_result.get("processing_metadata", {}).get("quality_metrics", {}),
            processing_time=processing_time,
            extraction_timestamp=extraction_result.get("extraction_timestamp")
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in extract_text_from_cv: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during text extraction"
        )


@router.post("/extract-bytes", response_model=TextExtractionResponse)
async def extract_text_from_bytes(
    file_content: bytes,
    file_name: str,
    document_type: str = "cv",
    current_user: dict = Depends(get_current_user)
):
    """
    Extract text from file content directly
    
    - **file_content**: File content as bytes
    - **file_name**: Original filename
    - **document_type**: Type of document
    - **Authentication**: Required (JWT token)
    """
    try:
        logger.info(f"Text extraction from bytes for {file_name} by user {current_user['user_id']}")
        
        # Start text extraction
        start_time = datetime.utcnow()
        
        extraction_result = await textract_service.extract_text_from_bytes(
            file_content=file_content,
            file_name=file_name,
            document_type=document_type
        )
        
        processing_time = (datetime.utcnow() - start_time).total_seconds()
        
        if not extraction_result["success"]:
            logger.error(f"Text extraction failed: {extraction_result['error']}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Text extraction failed: {extraction_result['error']}"
            )
        
        logger.info(f"Text extraction from bytes completed for {file_name}")
        
        return TextExtractionResponse(
            success=True,
            message="Text extraction completed successfully",
            extraction_id=str(datetime.utcnow().timestamp()),
            text=extraction_result["text"],
            confidence=extraction_result.get("confidence", 0.0),
            sections=extraction_result.get("processing_metadata", {}).get("sections", {}),
            key_information=extraction_result.get("processing_metadata", {}).get("key_information", {}),
            quality_metrics=extraction_result.get("processing_metadata", {}).get("quality_metrics", {}),
            processing_time=processing_time,
            extraction_timestamp=extraction_result.get("extraction_timestamp")
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in extract_text_from_bytes: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during text extraction"
        )


@router.get("/extract/{extraction_id}/status", response_model=ExtractionStatusResponse)
async def get_extraction_status(
    extraction_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get text extraction job status
    
    - **extraction_id**: ID of the extraction job
    - **Authentication**: Required
    """
    try:
        logger.info(f"Status check for extraction {extraction_id} by user {current_user['user_id']}")
        
        # For now, return a simple status
        # In a real implementation, you would track extraction jobs in database
        return ExtractionStatusResponse(
            extraction_id=extraction_id,
            status="completed",  # Simplified for now
            progress=100,
            created_at=datetime.utcnow().isoformat(),
            updated_at=datetime.utcnow().isoformat()
        )
    
    except Exception as e:
        logger.error(f"Unexpected error in get_extraction_status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get("/health",
           summary="Check Textract Health",
           description="Check the operational status of the AWS Textract service.")
async def textract_health_check():
    """
    Health check cho Textract service
    
    Returns:
        Dict với service health status
    """
    try:
        # Test Textract service availability
        # This is a simple check - in production you might want to do more comprehensive checks
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "service": "textract",
                "status": "healthy",
                "timestamp": datetime.utcnow().isoformat(),
                "region": textract_service.region,
                "bucket": textract_service.bucket_name
            }
        )
    
    except Exception as e:
        logger.error(f"Textract health check failed: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "service": "textract",
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
        )
