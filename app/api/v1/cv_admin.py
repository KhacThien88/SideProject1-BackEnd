"""
Admin CV Management API Endpoints
Admin có thể xem và quản lý tất cả CV files
"""
from fastapi import APIRouter, HTTPException, status, Depends, Request, Query
from fastapi.responses import JSONResponse, StreamingResponse
from typing import List, Dict, Any, Optional
import logging
from io import BytesIO

from app.core.security import verify_token
from app.models.user import User, UserRole
from app.services.auth_service import AuthService
from app.services.upload import upload_service
from app.services.s3 import s3_service
from app.services.textract import textract_service
from app.schemas.user import UserResponse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/cv", tags=["Admin CV Management"])
auth_service = AuthService()


def get_admin_user(request: Request) -> User:
    """Verify admin user from JWT token"""
    try:
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
                detail="Invalid token"
            )
        
        user = auth_service.user_repo.get_user_by_id(user_id)
        if not user or user.role != UserRole.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required"
            )
        
        return user
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error verifying admin user: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate admin credentials"
        )


@router.get("/all", response_model=List[Dict[str, Any]],
           summary="Liệt kê tất cả CV",
           description="Lấy danh sách tất cả CV trong hệ thống. Chỉ dành cho quản trị viên.")
async def list_all_cv_files(
    request: Request,
    limit: int = Query(default=50, le=100),
    admin_user: User = Depends(get_admin_user)
):
    """List all CV files from all users (Admin only)"""
    try:
        logger.info(f"Admin {admin_user.user_id} requesting all CV files")
        
        # Get all CV files from S3
        s3_result = await s3_service.list_user_files(
            user_id="",  # Empty to get all files
            file_type="cv",
            max_files=limit
        )
        
        if not s3_result["success"]:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to list files: {s3_result['error']}"
            )
        
        # Enhance with user information
        enhanced_files = []
        for file_info in s3_result["files"]:
            # Extract user_id from s3_key
            s3_key_parts = file_info["s3_key"].split("/")
            if len(s3_key_parts) >= 2:
                file_user_id = s3_key_parts[1]
                
                # Get user info
                user = auth_service.user_repo.get_user_by_id(file_user_id)
                user_info = {
                    "user_id": file_user_id,
                    "email": user.email if user else "Unknown",
                    "full_name": user.full_name if user else "Unknown"
                }
            else:
                user_info = {
                    "user_id": "Unknown",
                    "email": "Unknown",
                    "full_name": "Unknown"
                }
            
            enhanced_files.append({
                **file_info,
                "user_info": user_info
            })
        
        logger.info(f"Retrieved {len(enhanced_files)} CV files")
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "success": True,
                "files": enhanced_files,
                "total_count": len(enhanced_files)
            }
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing all CV files: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve CV files"
        )


@router.get("/user/{user_id}")
async def get_user_cv_files_admin(
    user_id: str,
    request: Request,
    admin_user: User = Depends(get_admin_user)
):
    """Get CV files for specific user (Admin only)"""
    try:
        logger.info(f"Admin {admin_user.user_id} requesting CV files for user {user_id}")
        
        # Get user info
        target_user = auth_service.user_repo.get_user_by_id(user_id)
        if not target_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Get user's CV files
        files_result = await upload_service.get_user_cv_files(user_id)
        
        if not files_result["success"]:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=files_result["error"]
            )
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "success": True,
                "user_info": {
                    "user_id": target_user.user_id,
                    "email": target_user.email,
                    "full_name": target_user.full_name
                },
                "files": files_result["files"],
                "total_count": files_result["total_count"]
            }
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user CV files: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve user CV files"
        )


@router.get("/download/{file_id}")
async def download_cv_file_admin(
    file_id: str,
    request: Request,
    admin_user: User = Depends(get_admin_user)
):
    """Download CV file by file_id (Admin only)"""
    try:
        logger.info(f"Admin {admin_user.user_id} downloading file {file_id}")
        
        # Get file metadata from database
        from app.core.database import get_dynamodb_resource
        from app.core.config import settings
        
        dynamodb = get_dynamodb_resource()
        table = dynamodb.Table(settings.cv_uploads_table_name)
        
        response = table.get_item(Key={'file_id': file_id})
        if 'Item' not in response:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found"
            )
        
        file_info = response['Item']
        s3_key = file_info['s3_key']
        filename = file_info['filename']
        
        # Download from S3
        download_result = await s3_service.download_file(s3_key)
        
        if not download_result["success"]:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found in storage"
            )
        
        # Return file as streaming response
        file_content = download_result["content"]
        content_type = download_result.get("content_type", "application/octet-stream")
        
        return StreamingResponse(
            BytesIO(file_content),
            media_type=content_type,
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading file {file_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to download file"
        )


@router.post("/extract/{file_id}")
async def extract_text_from_cv_admin(
    file_id: str,
    request: Request,
    admin_user: User = Depends(get_admin_user)
):
    """Extract text from CV file by file_id (Admin only)"""
    try:
        logger.info(f"Admin {admin_user.user_id} extracting text from file {file_id}")
        
        # Get file metadata from database
        from app.core.database import get_dynamodb_resource
        from app.core.config import settings
        
        dynamodb = get_dynamodb_resource()
        table = dynamodb.Table(settings.cv_uploads_table_name)
        
        response = table.get_item(Key={'file_id': file_id})
        if 'Item' not in response:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found"
            )
        
        file_info = response['Item']
        s3_key = file_info['s3_key']
        
        # Extract text using Textract
        extraction_result = await textract_service.extract_text_from_s3(
            s3_key=s3_key,
            document_type="cv"
        )
        
        if not extraction_result["success"]:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Text extraction failed: {extraction_result['error']}"
            )
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "success": True,
                "file_id": file_id,
                "s3_key": s3_key,
                "text": extraction_result["text"],
                "confidence": extraction_result.get("confidence", 0.0),
                "sections": extraction_result.get("processing_metadata", {}).get("sections", {}),
                "key_information": extraction_result.get("processing_metadata", {}).get("key_information", {}),
                "quality_metrics": extraction_result.get("processing_metadata", {}).get("quality_metrics", {}),
                "extraction_timestamp": extraction_result.get("extraction_timestamp")
            }
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error extracting text from file {file_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to extract text from file"
        )


@router.delete("/{file_id}")
async def delete_cv_file_admin(
    file_id: str,
    request: Request,
    admin_user: User = Depends(get_admin_user)
):
    """Delete CV file by file_id (Admin only)"""
    try:
        logger.info(f"Admin {admin_user.user_id} deleting file {file_id}")
        
        # Get file metadata from database
        from app.core.database import get_dynamodb_resource
        from app.core.config import settings
        
        dynamodb = get_dynamodb_resource()
        table = dynamodb.Table(settings.cv_uploads_table_name)
        
        response = table.get_item(Key={'file_id': file_id})
        if 'Item' not in response:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found"
            )
        
        file_info = response['Item']
        s3_key = file_info['s3_key']
        filename = file_info['filename']
        file_user_id = file_info['user_id']
        
        # Delete from S3
        try:
            await s3_service.delete_file(s3_key)
        except Exception as e:
            logger.warning(f"Failed to delete from S3: {str(e)}")
        
        # Delete from database
        table.delete_item(Key={'file_id': file_id})
        
        logger.info(f"File {file_id} ({filename}) deleted by admin {admin_user.user_id}")
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "success": True,
                "message": f"File {filename} deleted successfully",
                "file_id": file_id,
                "deleted_from_user": file_user_id
            }
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting file {file_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete file"
        )