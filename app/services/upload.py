"""
Upload Service
Xử lý logic upload CV files với validation, security và storage
"""

import os
import uuid
import hashlib
try:
    import magic
except ImportError:
    magic = None
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from fastapi import UploadFile
import boto3
from botocore.exceptions import ClientError
from decimal import Decimal

from app.core.config import settings
from app.core.database import get_dynamodb_resource
from app.utils.logger import get_logger
from app.utils.validators import validate_file_type, validate_file_size
from app.utils.helpers import convert_decimals
from app.services.s3 import s3_service

logger = get_logger(__name__)


class UploadService:
    """Service để xử lý upload CV files"""
    
    def __init__(self):
        self.dynamodb = get_dynamodb_resource()
        self.s3_service = s3_service
        
        # File validation settings
        self.allowed_extensions = {'.pdf', '.jpg', '.jpeg', '.png'}
        self.max_file_size = 10 * 1024 * 1024  # 10MB
        self.allowed_mime_types = {
            'application/pdf',
            'image/jpeg',
            'image/jpg', 
            'image/png'
        }
    
    async def validate_upload_file(self, file: UploadFile) -> Dict[str, Any]:
        """
        Validate uploaded file
        
        Args:
            file: UploadFile object
            
        Returns:
            Dict với validation result
        """
        try:
            # Kiểm tra file name
            if not file.filename:
                return {
                    "valid": False,
                    "error": "No filename provided"
                }
            
            # Kiểm tra file extension
            file_ext = os.path.splitext(file.filename.lower())[1]
            if file_ext not in self.allowed_extensions:
                return {
                    "valid": False,
                    "error": f"File type not allowed. Supported types: {', '.join(self.allowed_extensions)}"
                }
            
            # Đọc file content để check size và MIME type
            file_content = await file.read()
            file_size = len(file_content)
            
            # Kiểm tra file size
            if file_size > self.max_file_size:
                return {
                    "valid": False,
                    "error": f"File too large. Maximum size: {self.max_file_size // (1024*1024)}MB"
                }
            
            if file_size == 0:
                return {
                    "valid": False,
                    "error": "Empty file not allowed"
                }
            
            # Kiểm tra MIME type bằng magic
            if magic:
                try:
                    mime_type = magic.from_buffer(file_content, mime=True)
                    if mime_type not in self.allowed_mime_types:
                        return {
                            "valid": False,
                            "error": f"Invalid file type detected: {mime_type}"
                        }
                except Exception as e:
                    logger.warning(f"Could not detect MIME type: {str(e)}")
                    # Fallback: chỉ check extension
                    pass
            
            # Reset file pointer
            await file.seek(0)
            
            return {
                "valid": True,
                "file_size": file_size,
                "file_type": file_ext,
                "mime_type": mime_type if 'mime_type' in locals() else None
            }
            
        except Exception as e:
            logger.error(f"File validation error: {str(e)}")
            return {
                "valid": False,
                "error": f"File validation failed: {str(e)}"
            }
    
    async def check_rate_limit(self, user_id: str) -> Dict[str, Any]:
        """
        Kiểm tra rate limiting cho user
        
        Args:
            user_id: ID của user
            
        Returns:
            Dict với rate limit result
        """
        try:
            table = self.dynamodb.Table(settings.rate_limit_table_name)
            
            # Kiểm tra uploads trong 1 giờ qua
            one_hour_ago = datetime.utcnow() - timedelta(hours=1)
            
            response = table.query(
                IndexName='user_id-timestamp-index',
                KeyConditionExpression='user_id = :user_id AND upload_timestamp > :one_hour_ago',
                ExpressionAttributeValues={
                    ':user_id': user_id,
                    ':one_hour_ago': one_hour_ago.isoformat()
                }
            )
            
            # Cho phép tối đa 5 uploads trong 1 giờ
            max_uploads_per_hour = 5
            current_uploads = len(response['Items'])
            
            if current_uploads >= max_uploads_per_hour:
                return {
                    "allowed": False,
                    "current_uploads": current_uploads,
                    "max_uploads": max_uploads_per_hour,
                    "reset_time": (datetime.utcnow() + timedelta(hours=1)).isoformat()
                }
            
            return {
                "allowed": True,
                "current_uploads": current_uploads,
                "max_uploads": max_uploads_per_hour
            }
            
        except Exception as e:
            logger.error(f"Rate limit check error: {str(e)}")
            # Trong trường hợp lỗi, cho phép upload
            return {"allowed": True, "error": str(e)}
    
    async def process_cv_upload(
        self, 
        file: UploadFile, 
        user_id: str, 
        user_email: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process CV upload với storage và database
        
        Args:
            file: UploadFile object
            user_id: ID của user
            user_email: Email của user (optional)
            
        Returns:
            Dict với upload result
        """
        try:
            # Tạo unique file ID (sử dụng chung cho S3 metadata và DynamoDB)
            file_id = str(uuid.uuid4())
            timestamp = datetime.utcnow()
            
            # Đọc file content
            file_content = await file.read()
            file_size = len(file_content)
            
            # Upload to S3 using S3Service
            s3_result = await self.s3_service.upload_file(
                file_content=file_content,
                file_name=file.filename,
                user_id=user_id,
                file_type="cv",
                content_type=file.content_type,
                file_id=file_id
            )
            
            if not s3_result["success"]:
                return {
                    "success": False,
                    "error": f"S3 upload failed: {s3_result['error']}"
                }
            
            # Lưu metadata vào DynamoDB
            db_result = await self._save_upload_metadata(
                file_id=file_id,
                user_id=user_id,
                user_email=user_email,
                filename=file.filename,
                file_size=file_size,
                file_type=os.path.splitext(file.filename)[1],
                s3_key=s3_result["s3_key"],
                s3_url=s3_result["file_url"],
                upload_timestamp=timestamp
            )
            
            if not db_result["success"]:
                # Rollback: xóa file khỏi S3
                try:
                    await self.s3_service.delete_file(s3_result["s3_key"])
                except Exception as e:
                    logger.error(f"Failed to rollback S3 upload: {str(e)}")
                
                return {
                    "success": False,
                    "error": f"Database save failed: {db_result['error']}"
                }
            
            # Log rate limiting
            await self._log_upload_activity(user_id, file_id, timestamp)
            
            logger.info(f"CV upload successful: {file_id} for user {user_id}")
            
            return {
                "success": True,
                "file_id": file_id,
                "file_url": s3_result["file_url"],
                "file_size": file_size,
                "file_type": os.path.splitext(file.filename)[1],
                "upload_timestamp": timestamp.isoformat(),
                "s3_key": s3_result["s3_key"]
            }
            
        except Exception as e:
            logger.error(f"CV upload processing error: {str(e)}")
            return {
                "success": False,
                "error": f"Upload processing failed: {str(e)}"
            }
    
    async def get_upload_status(self, file_id: str, user_id: str) -> Dict[str, Any]:
        """
        Lấy trạng thái upload của file
        
        Args:
            file_id: ID của file
            user_id: ID của user
            
        Returns:
            Dict với status information
        """
        try:
            table = self.dynamodb.Table(settings.cv_uploads_table_name)
            
            response = table.get_item(
                Key={'file_id': file_id}
            )
            
            if 'Item' not in response:
                return {
                    "success": False,
                    "error": "File not found"
                }
            
            item = response['Item']
            
            # Convert Decimal values to int/float for JSON serialization
            converted_item = convert_decimals(item)
            
            # Kiểm tra ownership
            if converted_item['user_id'] != user_id:
                return {
                    "success": False,
                    "error": "Access denied"
                }
            
            return {
                "success": True,
                "file_id": converted_item['file_id'],
                "status": converted_item.get('status', 'pending'),
                "progress": converted_item.get('progress', 0),
                "error_message": converted_item.get('error_message'),
                "created_at": converted_item['created_at'],
                "updated_at": converted_item['updated_at']
            }
            
        except Exception as e:
            logger.error(f"Get upload status error: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def delete_cv_file(self, file_id: str, user_id: str) -> Dict[str, Any]:
        """
        Xóa CV file
        
        Args:
            file_id: ID của file
            user_id: ID của user
            
        Returns:
            Dict với delete result
        """
        try:
            table = self.dynamodb.Table(settings.cv_uploads_table_name)
            
            # Lấy file info
            response = table.get_item(Key={'file_id': file_id})
            if 'Item' not in response:
                return {
                    "success": False,
                    "error": "File not found"
                }
            
            item = response['Item']
            
            # Convert Decimal values to int/float for JSON serialization
            converted_item = convert_decimals(item)
            
            # Kiểm tra ownership
            if converted_item['user_id'] != user_id:
                return {
                    "success": False,
                    "error": "Access denied"
                }
            
            # Xóa từ S3
            try:
                await self.s3_service.delete_file(converted_item['s3_key'])
            except Exception as e:
                logger.warning(f"Failed to delete from S3: {str(e)}")
            
            # Xóa từ database
            table.delete_item(Key={'file_id': file_id})
            
            logger.info(f"CV file deleted: {file_id} by user {user_id}")
            
            return {
                "success": True,
                "message": "File deleted successfully"
            }
            
        except Exception as e:
            logger.error(f"Delete CV file error: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_user_cv_files(self, user_id: str) -> Dict[str, Any]:
        """
        Lấy danh sách CV files của user
        
        Args:
            user_id: ID của user
            
        Returns:
            Dict với files list
        """
        try:
            table = self.dynamodb.Table(settings.cv_uploads_table_name)
            
            response = table.query(
                IndexName='user_id-created_at-index',
                KeyConditionExpression='user_id = :user_id',
                ExpressionAttributeValues={':user_id': user_id},
                ScanIndexForward=False  # Sort by created_at descending
            )
            
            files = []
            for item in response['Items']:
                # Convert Decimal values to int/float for JSON serialization
                converted_item = convert_decimals(item)
                files.append({
                    "file_id": converted_item['file_id'],
                    "filename": converted_item['filename'],
                    "file_size": converted_item['file_size'],
                    "file_type": converted_item['file_type'],
                    "status": converted_item.get('status', 'pending'),
                    "created_at": converted_item['created_at'],
                    "updated_at": converted_item['updated_at']
                })
            
            return {
                "success": True,
                "files": files,
                "total_count": len(files)
            }
            
        except Exception as e:
            logger.error(f"Get user CV files error: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    
    async def _save_upload_metadata(
        self,
        file_id: str,
        user_id: str,
        user_email: Optional[str],
        filename: str,
        file_size: int,
        file_type: str,
        s3_key: str,
        s3_url: str,
        upload_timestamp: datetime
    ) -> Dict[str, Any]:
        """Save upload metadata to DynamoDB"""
        try:
            table = self.dynamodb.Table(settings.cv_uploads_table_name)
            
            item = {
                'file_id': file_id,
                'user_id': user_id,
                'user_email': user_email,
                'filename': filename,
                'file_size': file_size,
                'file_type': file_type,
                's3_key': s3_key,
                's3_url': s3_url,
                'status': 'pending',
                'progress': 0,
                'created_at': upload_timestamp.isoformat(),
                'updated_at': upload_timestamp.isoformat()
            }
            
            table.put_item(Item=item)
            
            return {"success": True}
            
        except Exception as e:
            logger.error(f"Save metadata error: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _log_upload_activity(
        self, 
        user_id: str, 
        file_id: str, 
        timestamp: datetime
    ) -> None:
        """Log upload activity for rate limiting"""
        try:
            table = self.dynamodb.Table(settings.rate_limit_table_name)
            
            item = {
                'id': f"{user_id}_{timestamp.isoformat()}",
                'user_id': user_id,
                'file_id': file_id,
                'upload_timestamp': timestamp.isoformat()
            }
            
            table.put_item(Item=item)
            
        except Exception as e:
            logger.error(f"Log upload activity error: {str(e)}")


# Singleton instance
upload_service = UploadService()

