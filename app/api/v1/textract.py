"""
Textract API Endpoints
Handle text extraction from CV documents
"""

import logging
import json
from datetime import datetime
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request, Path, Query
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
    force: bool = Field(default=False, description="Force re-extraction even if cached result exists")


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
    structured_json: Optional[Dict[str, Any]] = None
    structured_json_s3_key: Optional[str] = None


class ExtractionStatusResponse(BaseModel):
    """Response model cho extraction status"""
    extraction_id: str
    status: str  # pending, processing, completed, failed
    progress: Optional[int] = None
    error_message: Optional[str] = None
    created_at: str
    updated_at: str


class StructuredJsonResponse(BaseModel):
    """Response model cho structured JSON đã được lưu ở S3"""
    success: bool
    message: str
    document_type: str
    user_id: str
    file_id: str
    s3_key: Optional[str] = None
    presigned_url: Optional[str] = None
    json: Optional[Dict[str, Any]] = None


class JDTextExtractionRequest(BaseModel):
    s3_key: str = Field(..., description="S3 key of the JD file to extract")
    force: bool = Field(default=False, description="Force re-extraction even if cached result exists")


class CVTextExtractionRequest(BaseModel):
    s3_key: str = Field(..., description="S3 key of the CV file to extract")
    force: bool = Field(default=False, description="Force re-extraction even if cached result exists")


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
    extraction_request: CVTextExtractionRequest,
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
        if current_user["role"] != "admin" and not extraction_request.s3_key.startswith(f"User_Upload/CV_raw/{current_user['user_id']}/"):
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
            document_type="cv",
            force=extraction_request.force
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
            extraction_timestamp=extraction_result.get("extraction_timestamp"),
            structured_json=extraction_result.get("structured_json"),
            structured_json_s3_key=extraction_result.get("structured_json_s3_key")
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in extract_text_from_cv: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during text extraction"
        )


@router.post("/extract-jd", response_model=TextExtractionResponse,
            summary="Extract Text from S3 (JD)",
            description="Extract text from JD uploaded to S3 using AWS Textract. Only recruiter/admin can access.")
async def extract_text_from_jd(
    extraction_request: JDTextExtractionRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Extract text from JD document in S3 for recruiters
    """
    try:
        if current_user["role"] not in ["recruiter", "admin"]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Recruiter role required")

        # Verify JD path access
        if current_user["role"] != "admin" and not extraction_request.s3_key.startswith(f"User_Upload/JD_raw/{current_user['user_id']}/"):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to this file")

        # Ensure document_type is jd
        document_type = "jd"

        file_metadata = await s3_service.get_file_metadata(extraction_request.s3_key)
        if not file_metadata["success"]:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")

        start_time = datetime.utcnow()
        extraction_result = await textract_service.extract_text_from_s3(
            s3_key=extraction_request.s3_key,
            document_type=document_type,
            force=extraction_request.force
        )
        processing_time = (datetime.utcnow() - start_time).total_seconds()

        if not extraction_result["success"]:
            logger.error(f"JD text extraction failed: {extraction_result['error']}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Text extraction failed: {extraction_result['error']}")

        return TextExtractionResponse(
            success=True,
            message="JD text extraction completed successfully",
            extraction_id=extraction_result.get("extraction_timestamp", str(datetime.utcnow().timestamp())),
            text=extraction_result["text"],
            confidence=extraction_result.get("confidence", 0.0),
            sections=extraction_result.get("processing_metadata", {}).get("sections", {}),
            key_information=extraction_result.get("processing_metadata", {}).get("key_information", {}),
            quality_metrics=extraction_result.get("processing_metadata", {}).get("quality_metrics", {}),
            processing_time=processing_time,
            extraction_timestamp=extraction_result.get("extraction_timestamp"),
            structured_json=extraction_result.get("structured_json"),
            structured_json_s3_key=extraction_result.get("structured_json_s3_key")
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in extract_text_from_jd: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error during text extraction")


 


 


    
    
@router.get(
    "/structured-json",
    response_model=StructuredJsonResponse,
    summary="Fetch structured JSON by original S3 key",
    description=(
        "Nhận JSON đã xử lý bằng cách truyền s3_key của file gốc. Hệ thống tự đọc metadata để xác định {user_id, file_id} và trả JSON từ Processed/{CV_Json|JD_Json}."
    ),
)
async def get_structured_json_by_s3_key(
    s3_key: str = Query(..., description="S3 key của file gốc đã upload (User_Upload/...)"),
    document_type: str = Query("cv", pattern="^(cv|jd)$", description="Loại tài liệu: cv hoặc jd"),
    current_user: dict = Depends(get_current_user)
):
    try:
        # Authorization: admin được phép tất cả; user chỉ được đọc file của mình
        if current_user["role"] != "admin":
            required_prefix = f"User_Upload/CV_raw/{current_user['user_id']}/"
            jd_prefix = f"User_Upload/JD_raw/{current_user['user_id']}/"
            if not (s3_key.startswith(required_prefix) or s3_key.startswith(jd_prefix)):
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to this file")

        # Lấy metadata để suy ra user_id và file_id
        meta = await s3_service.get_file_metadata(s3_key)
        if not meta.get("success"):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source file not found")
        md = meta.get("metadata", {})
        user_id = md.get("user_id") or current_user["user_id"]
        file_id = md.get("file_id")
        if not file_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing file_id in source metadata")

        processed_folder = "Processed/CV_Json" if document_type == "cv" else "Processed/JD_Json"
        json_key = f"{processed_folder}/{user_id}/{file_id}.json"

        dl = await s3_service.download_file(json_key)
        if not dl.get("success"):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Structured JSON not found")

        try:
            content_bytes = dl["content"]
            parsed_json = json.loads(content_bytes.decode("utf-8"))
        except Exception:
            parsed_json = None

        presigned = await s3_service.generate_presigned_url(json_key, expiration=3600)
        presigned_url = presigned.get("url") if presigned.get("success") else None

        return StructuredJsonResponse(
            success=True,
            message="Structured JSON fetched successfully",
            document_type=document_type,
            user_id=user_id,
            file_id=file_id,
            s3_key=json_key,
            presigned_url=presigned_url,
            json=parsed_json
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in get_structured_json_by_s3_key: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")



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
