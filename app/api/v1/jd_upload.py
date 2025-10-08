"""
JD Upload API Endpoints
Handle JD (Job Description) file uploads with validation and security
"""

import logging
import uuid
import hashlib
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.core.security import verify_token
from app.services.upload import UploadService
from app.utils.validators import validate_file_type, validate_file_size
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(tags=["JD Upload"])

# Upload service instance
upload_service = UploadService()


class JDUploadResponse(BaseModel):
    """Response model cho JD upload operations"""
    success: bool
    message: str
    file_id: Optional[str] = None
    file_url: Optional[str] = None
    file_size: Optional[int] = None
    file_type: Optional[str] = None
    upload_timestamp: Optional[str] = None


class JDUploadStatusResponse(BaseModel):
    """Response model cho JD upload status"""
    file_id: str
    status: str  # pending, processing, completed, failed
    progress: Optional[int] = None
    error_message: Optional[str] = None
    created_at: str
    updated_at: str


class JDFileInfo(BaseModel):
    """Model cho thông tin JD file"""
    file_id: str
    filename: str
    file_size: int
    file_type: str
    status: str
    created_at: str
    updated_at: str


class JDListResponse(BaseModel):
    """Response model cho list JD files"""
    success: bool
    files: List[JDFileInfo]
    total_count: int


async def get_current_user(request: Request):
    """Dependency to get current user from JWT token"""
    try:
        # Get token from Authorization header
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing or invalid authorization header"
            )
        
        token = auth_header.split(" ")[1]
        payload = verify_token(token, "access")
        user_id = payload.get("user_id")
        
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload"
            )
        
        return {"user_id": user_id, "email": payload.get("email"), "role": payload.get("role", "recruiter")}
    
    except Exception as e:
        logger.error(f"Authentication error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed"
        )


@router.post("/jd", response_model=JDUploadResponse,
            summary="Upload JD",
            description="Upload Job Description file (PDF, JPG, JPEG, PNG). Automatically validates file type and size.")
async def upload_jd(
    request: Request,
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """
    Upload JD file with validation and security
    
    - **file**: JD file (PDF, JPG, JPEG, PNG) - max 10MB
    - **Authentication**: Required (JWT token)
    - **Rate limiting**: Applied
    """
    try:
        logger.info(f"JD upload attempt by user {current_user['user_id']}")
        
        # Validate file
        validation_result = await upload_service.validate_upload_file(file)
        if not validation_result["valid"]:
            logger.warning(f"File validation failed: {validation_result['error']}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=validation_result["error"]
            )
        
        # Check rate limiting
        rate_limit_result = await upload_service.check_rate_limit(
            current_user["user_id"]
        )
        if not rate_limit_result["allowed"]:
            logger.warning(f"Rate limit exceeded for user {current_user['user_id']}")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many upload requests. Please wait before trying again."
            )
        
        # Process JD upload using dedicated method
        upload_result = await upload_service.process_jd_upload(
            file=file,
            user_id=current_user["user_id"],
            user_email=current_user.get("email")
        )
        
        if not upload_result["success"]:
            logger.error(f"JD upload processing failed: {upload_result['error']}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="JD upload processing failed"
            )
        
        logger.info(f"JD uploaded successfully: {upload_result['file_id']}")
        
        return JDUploadResponse(
            success=True,
            message="JD uploaded successfully",
            file_id=upload_result["file_id"],
            file_url=upload_result.get("file_url"),
            file_size=upload_result.get("file_size"),
            file_type=upload_result.get("file_type"),
            upload_timestamp=upload_result.get("upload_timestamp")
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in upload_jd: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during JD upload"
        )


@router.get("/jd/{file_id}/status", response_model=JDUploadStatusResponse,
           summary="Check JD Upload Status",
           description="Get the current status of the uploaded JD file (pending, processing, completed, failed).")
async def get_jd_upload_status(
    file_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get the upload status of JD file
    
    - **file_id**: ID of the uploaded file
    - **Authentication**: Required
    """
    try:
        logger.info(f"JD status check for file {file_id} by user {current_user['user_id']}")
        
        status_result = await upload_service.get_upload_status(
            file_id=file_id,
            user_id=current_user["user_id"]
        )
        
        if not status_result["success"]:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=status_result["error"]
            )
        
        return JDUploadStatusResponse(
            file_id=status_result["file_id"],
            status=status_result["status"],
            progress=status_result.get("progress"),
            error_message=status_result.get("error_message"),
            created_at=status_result["created_at"],
            updated_at=status_result["updated_at"]
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in get_jd_upload_status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.delete("/jd/{file_id}")
async def delete_jd(
    file_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Delete uploaded JD file
    
    - **file_id**: ID of the file to delete
    - **Authentication**: Required
    """
    try:
        logger.info(f"JD delete request for file {file_id} by user {current_user['user_id']}")
        
        delete_result = await upload_service.delete_cv_file(
            file_id=file_id,
            user_id=current_user["user_id"]
        )
        
        if not delete_result["success"]:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=delete_result["error"]
            )
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "success": True,
                "message": "JD file deleted successfully",
                "file_id": file_id
            }
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in delete_jd: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get("/jd/user/{user_id}", response_model=JDListResponse,
           summary="Get User JD Files",
           description="Get list of JD files for a specific user. Only the owner or admin can access.")
async def get_user_jd_files(
    user_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get list of JD files for user
    
    - **user_id**: ID of the user (must match current user)
    - **Authentication**: Required
    """
    try:
        # Check if user has access permission
        # Admin can access any user's files, regular users can only access their own files
        if current_user["role"] != "admin" and current_user["user_id"] != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        logger.info(f"List JD files for user {user_id}")
        
        # Use upload service to list JD files
        files_result = await upload_service.get_user_jd_files(user_id)
        
        if not files_result["success"]:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=files_result["error"]
            )
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "success": True,
                "files": files_result["files"],
                "total_count": files_result["total_count"]
            }
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in get_user_jd_files: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )
