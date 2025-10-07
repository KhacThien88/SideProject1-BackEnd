"""
S3 Service
Comprehensive S3 integration cho file storage với proper organization, security và lifecycle management
"""

import boto3
import uuid
import hashlib
import os
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, BinaryIO
from botocore.exceptions import ClientError, NoCredentialsError
from botocore.config import Config

from app.core.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class S3Service:
    """Service để quản lý S3 operations với security và organization"""
    
    def __init__(self):
        """Initialize S3 service với AWS credentials. Nếu thiếu credentials, vô hiệu hóa S3 thay vì crash."""
        try:
            # Nếu cấu hình tắt S3, vô hiệu hóa ngay
            if hasattr(settings, 'use_s3') and not settings.use_s3:
                logger.info("S3 is disabled by configuration (use_s3=False)")
                self.s3_client = None
                self.bucket_name = settings.s3_bucket_name
                self.region = settings.aws_region
                return
            # Kiểm tra nếu đang chạy test thì skip verification
            if getattr(settings, 'test_mode', False):
                logger.info("Running in test mode, skipping S3 bucket verification")
                self.s3_client = None
                self.bucket_name = settings.s3_bucket_name
                self.region = settings.aws_region
                return

            # Configure AWS client với retry config
            config = Config(
                region_name=settings.aws_region,
                retries={'max_attempts': 3, 'mode': 'adaptive'}
            )

            # Initialize S3 client
            if settings.aws_access_key_id and settings.aws_secret_access_key:
                self.s3_client = boto3.client(
                    's3',
                    aws_access_key_id=settings.aws_access_key_id,
                    aws_secret_access_key=settings.aws_secret_access_key,
                    region_name=settings.aws_region,
                    config=config
                )
            else:
                # Use default credentials (IAM role, profile, etc.)
                self.s3_client = boto3.client('s3', region_name=settings.aws_region, config=config)

            self.bucket_name = settings.s3_bucket_name
            self.region = settings.aws_region

            # Verify bucket exists
            try:
                self._verify_bucket_exists()
                logger.info(f"S3Service initialized with bucket: {self.bucket_name}")
            except NoCredentialsError:
                # Thiếu credentials: vô hiệu hóa S3 thay vì crash
                logger.warning("AWS credentials not found. Disabling S3 integration for this run.")
                self.s3_client = None
                return

        except NoCredentialsError:
            # Trường hợp phát sinh sớm hơn
            logger.warning("AWS credentials not found during client init. Disabling S3 integration.")
            self.s3_client = None
            self.bucket_name = settings.s3_bucket_name
            self.region = settings.aws_region
        except Exception as e:
            logger.error(f"Failed to initialize S3Service: {str(e)}")
            # Không crash app: vô hiệu hóa S3
            self.s3_client = None
            self.bucket_name = getattr(settings, 's3_bucket_name', '')
            self.region = getattr(settings, 'aws_region', 'us-east-1')
    
    def _verify_bucket_exists(self) -> bool:
        """Verify S3 bucket exists và accessible"""
        try:
            self.s3_client.head_bucket(Bucket=self.bucket_name)
            return True
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404':
                logger.error(f"S3 bucket {self.bucket_name} not found")
                raise Exception(f"S3 bucket {self.bucket_name} not found")
            elif error_code == '403':
                logger.error(f"Access denied to S3 bucket {self.bucket_name}")
                raise Exception(f"Access denied to S3 bucket {self.bucket_name}")
            else:
                logger.error(f"Error accessing S3 bucket: {str(e)}")
                raise
    
    async def upload_file(
        self,
        file_content: bytes,
        file_name: str,
        user_id: str,
        file_type: str = "cv",
        content_type: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
        file_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Upload file to S3 với proper organization"""
        try:
            if not self.s3_client:
                return {"success": False, "error": "S3 is disabled (no AWS credentials)."}
            file_id = file_id or str(uuid.uuid4())
            timestamp = datetime.utcnow()
            
            s3_key = self._generate_s3_key(user_id, file_type, file_id, file_name)
            content_type = content_type or self._get_content_type(file_name)
            
            s3_metadata = {
                'user_id': user_id,
                'file_id': file_id,
                'file_type': file_type,
                'original_filename': file_name,
                'upload_timestamp': timestamp.isoformat(),
                'file_size': str(len(file_content))
            }
            
            if metadata:
                s3_metadata.update(metadata)
            
            upload_result = self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=file_content,
                ContentType=content_type,
                Metadata=s3_metadata,
                ServerSideEncryption='AES256',
                StorageClass='STANDARD'
            )
            
            file_url = self._generate_presigned_url(s3_key, expiration=3600)
            
            logger.info(f"File uploaded successfully: {s3_key}")
            
            return {
                "success": True,
                "file_id": file_id,
                "s3_key": s3_key,
                "file_url": file_url,
                "file_size": len(file_content),
                "content_type": content_type,
                "upload_timestamp": timestamp.isoformat(),
                "etag": upload_result.get('ETag', '').strip('"')
            }
            
        except Exception as e:
            logger.error(f"Failed to upload file: {str(e)}")
            return {"success": False, "error": str(e)}

    async def find_s3_key_by_file_id(self, file_id: str, max_scan: int = 2000) -> Dict[str, Any]:
        """
        Tìm object key trong S3 theo metadata file_id (fallback khi DB thiếu bản ghi)
        Cảnh báo: thao tác này quét theo prefix chung và head_object để đối chiếu metadata.
        """
        try:
            if not self.s3_client:
                return {"success": False, "error": "S3 is disabled (no AWS credentials)."}

            prefix = "user-uploads/"
            paginator = self.s3_client.get_paginator('list_objects_v2')
            pages = paginator.paginate(Bucket=self.bucket_name, Prefix=prefix, PaginationConfig={"MaxItems": max_scan})

            for page in pages:
                for obj in page.get('Contents', []):
                    key = obj['Key']
                    try:
                        head = self.s3_client.head_object(Bucket=self.bucket_name, Key=key)
                        md = head.get('Metadata', {})
                        if md.get('file_id') == file_id:
                            return {
                                "success": True,
                                "s3_key": key,
                                "metadata": md,
                                "content_type": head.get('ContentType')
                            }
                    except Exception:
                        continue

            return {"success": False, "error": "File not found"}
        except Exception as e:
            logger.error(f"Failed to find s3 key by file_id {file_id}: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def download_file(self, s3_key: str) -> Dict[str, Any]:
        """
        Download file from S3
        
        Args:
            s3_key: S3 object key
            
        Returns:
            Dict với download result
        """
        try:
            if not self.s3_client:
                return {"success": False, "error": "S3 is disabled (no AWS credentials)."}
            response = self.s3_client.get_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )
            
            file_content = response['Body'].read()
            metadata = response.get('Metadata', {})
            
            return {
                "success": True,
                "content": file_content,
                "content_type": response.get('ContentType'),
                "metadata": metadata,
                "size": len(file_content)
            }
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'NoSuchKey':
                return {
                    "success": False,
                    "error": "File not found"
                }
            else:
                logger.error(f"Failed to download file {s3_key}: {str(e)}")
                return {
                    "success": False,
                    "error": str(e)
                }
        except Exception as e:
            logger.error(f"Download error: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def delete_file(self, s3_key: str) -> Dict[str, Any]:
        """
        Delete file from S3
        
        Args:
            s3_key: S3 object key
            
        Returns:
            Dict với delete result
        """
        try:
            if not self.s3_client:
                return {"success": False, "error": "S3 is disabled (no AWS credentials)."}
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )
            
            logger.info(f"File deleted successfully: {s3_key}")
            
            return {
                "success": True,
                "message": "File deleted successfully"
            }
            
        except ClientError as e:
            logger.error(f"Failed to delete file {s3_key}: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
        except Exception as e:
            logger.error(f"Delete error: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def list_user_files(
        self, 
        user_id: str, 
        file_type: Optional[str] = None,
        max_files: int = 100
    ) -> Dict[str, Any]:
        """
        List files của user trong S3, hoặc tất cả files nếu user_id rỗng
        
        Args:
            user_id: ID của user (empty string để lấy tất cả files)
            file_type: Type of files to filter (optional)
            max_files: Maximum number of files to return
            
        Returns:
            Dict với files list
        """
        try:
            if not self.s3_client:
                return {"success": False, "error": "S3 is disabled (no AWS credentials)."}
            
            # Create prefix for user files
            if user_id:
                prefix = f"user-uploads/{user_id}/"
                if file_type:
                    prefix += f"{file_type}/"
            else:
                # List all files if user_id is empty
                prefix = "user-uploads/"
                if file_type:
                    # For all users with specific file type, we need to scan differently
                    prefix = f"user-uploads/"
            
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix,
                MaxKeys=max_files
            )
            
            files = []
            for obj in response.get('Contents', []):
                # Filter by file type if specified and user_id is empty
                if not user_id and file_type:
                    # Check if the file path contains the file type
                    if f"/{file_type}/" not in obj['Key']:
                        continue
                
                # Get object metadata
                try:
                    head_response = self.s3_client.head_object(
                        Bucket=self.bucket_name,
                        Key=obj['Key']
                    )
                    metadata = head_response.get('Metadata', {})
                    
                    files.append({
                        "s3_key": obj['Key'],
                        "file_id": metadata.get('file_id', ''),
                        "original_filename": metadata.get('original_filename', ''),
                        "file_type": metadata.get('file_type', ''),
                        "file_size": int(metadata.get('file_size', 0)),
                        "upload_timestamp": metadata.get('upload_timestamp', ''),
                        "last_modified": obj['LastModified'].isoformat(),
                        "etag": obj['ETag'].strip('"')
                    })
                except Exception as e:
                    logger.warning(f"Failed to get metadata for {obj['Key']}: {str(e)}")
                    continue
            
            return {
                "success": True,
                "files": files,
                "total_count": len(files),
                "prefix": prefix
            }
            
        except Exception as e:
            logger.error(f"Failed to list user files: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def generate_presigned_url(
        self, 
        s3_key: str, 
        expiration: int = 3600,
        operation: str = 'get_object'
    ) -> Dict[str, Any]:
        """
        Generate pre-signed URL cho file access
        
        Args:
            s3_key: S3 object key
            expiration: URL expiration time in seconds
            operation: S3 operation (get_object, put_object)
            
        Returns:
            Dict với presigned URL
        """
        try:
            if not self.s3_client:
                return {"success": False, "error": "S3 is disabled (no AWS credentials)."}
            url = self.s3_client.generate_presigned_url(
                operation,
                Params={'Bucket': self.bucket_name, 'Key': s3_key},
                ExpiresIn=expiration
            )
            
            return {
                "success": True,
                "url": url,
                "expiration": expiration,
                "expires_at": (datetime.utcnow() + timedelta(seconds=expiration)).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to generate presigned URL: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def copy_file(
        self, 
        source_key: str, 
        destination_key: str,
        metadata: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Copy file trong S3
        
        Args:
            source_key: Source S3 key
            destination_key: Destination S3 key
            metadata: Additional metadata for destination
            
        Returns:
            Dict với copy result
        """
        try:
            if not self.s3_client:
                return {"success": False, "error": "S3 is disabled (no AWS credentials)."}
            copy_source = {
                'Bucket': self.bucket_name,
                'Key': source_key
            }
            
            copy_params = {
                'Bucket': self.bucket_name,
                'Key': destination_key,
                'CopySource': copy_source,
                'ServerSideEncryption': 'AES256'
            }
            
            if metadata:
                copy_params['Metadata'] = metadata
                copy_params['MetadataDirective'] = 'REPLACE'
            
            response = self.s3_client.copy_object(**copy_params)
            
            logger.info(f"File copied successfully: {source_key} -> {destination_key}")
            
            return {
                "success": True,
                "source_key": source_key,
                "destination_key": destination_key,
                "etag": response.get('CopyObjectResult', {}).get('ETag', '').strip('"')
            }
            
        except Exception as e:
            logger.error(f"Failed to copy file: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_file_metadata(self, s3_key: str) -> Dict[str, Any]:
        """
        Get file metadata từ S3
        
        Args:
            s3_key: S3 object key
            
        Returns:
            Dict với file metadata
        """
        try:
            if not self.s3_client:
                return {"success": False, "error": "S3 is disabled (no AWS credentials)."}
            response = self.s3_client.head_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )
            
            return {
                "success": True,
                "metadata": response.get('Metadata', {}),
                "content_type": response.get('ContentType'),
                "content_length": response.get('ContentLength'),
                "last_modified": response.get('LastModified'),
                "etag": response.get('ETag', '').strip('"'),
                "storage_class": response.get('StorageClass', 'STANDARD')
            }
            
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                return {
                    "success": False,
                    "error": "File not found"
                }
            else:
                logger.error(f"Failed to get file metadata: {str(e)}")
                return {
                    "success": False,
                    "error": str(e)
                }
        except Exception as e:
            logger.error(f"Get metadata error: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _generate_s3_key(
        self, 
        user_id: str, 
        file_type: str, 
        file_id: str, 
        original_filename: str
    ) -> str:
        """Generate organized S3 key"""
        # Sanitize filename
        safe_filename = self._sanitize_filename(original_filename)
        
        # Create organized path: user-uploads/{user_id}/{file_type}/{file_id}_{filename}
        s3_key = f"user-uploads/{user_id}/{file_type}/{file_id}_{safe_filename}"
        
        return s3_key
    
    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename để tránh issues"""
        import re
        
        # Remove path components
        filename = filename.split('/')[-1]
        
        # Remove special characters
        filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
        
        # Remove multiple underscores
        filename = re.sub(r'_+', '_', filename)
        
        # Remove leading/trailing underscores
        filename = filename.strip('_')
        
        # Ensure filename is not empty
        if not filename:
            filename = "unnamed_file"
        
        return filename
    
    def _get_content_type(self, filename: str) -> str:
        """Determine content type from filename"""
        import mimetypes
        
        content_type, _ = mimetypes.guess_type(filename)
        
        if content_type:
            return content_type
        
        # Fallback based on extension
        ext = filename.lower().split('.')[-1]
        content_type_map = {
            'pdf': 'application/pdf',
            'doc': 'application/msword',
            'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'txt': 'text/plain',
            'jpg': 'image/jpeg',
            'jpeg': 'image/jpeg',
            'png': 'image/png'
        }
        
        return content_type_map.get(ext, 'application/octet-stream')
    
    def _generate_presigned_url(self, s3_key: str, expiration: int = 3600) -> str:
        """Generate presigned URL"""
        return self.s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': self.bucket_name, 'Key': s3_key},
            ExpiresIn=expiration
        )
    
    async def setup_lifecycle_policy(self) -> Dict[str, Any]:
        """
        Setup S3 lifecycle policy cho cost optimization
        
        Returns:
            Dict với setup result
        """
        try:
            lifecycle_config = {
                'Rules': [
                    {
                        'ID': 'CV_Uploads_Lifecycle',
                        'Status': 'Enabled',
                        'Filter': {
                            'Prefix': 'user-uploads/'
                        },
                        'Transitions': [
                            {
                                'Days': 30,
                                'StorageClass': 'STANDARD_IA'
                            },
                            {
                                'Days': 90,
                                'StorageClass': 'GLACIER'
                            }
                        ],
                        'Expiration': {
                            'Days': 365  # Delete after 1 year
                        }
                    }
                ]
            }
            
            self.s3_client.put_bucket_lifecycle_configuration(
                Bucket=self.bucket_name,
                LifecycleConfiguration=lifecycle_config
            )
            
            logger.info("S3 lifecycle policy configured successfully")
            
            return {
                "success": True,
                "message": "Lifecycle policy configured"
            }
            
        except Exception as e:
            logger.error(f"Failed to setup lifecycle policy: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_bucket_info(self) -> Dict[str, Any]:
        """
        Get S3 bucket information
        
        Returns:
            Dict với bucket info
        """
        try:
            # Get bucket location
            location_response = self.s3_client.get_bucket_location(
                Bucket=self.bucket_name
            )
            
            # Get bucket versioning
            try:
                versioning_response = self.s3_client.get_bucket_versioning(
                    Bucket=self.bucket_name
                )
                versioning_status = versioning_response.get('Status', 'Disabled')
            except:
                versioning_status = 'Unknown'
            
            # Get bucket encryption
            try:
                encryption_response = self.s3_client.get_bucket_encryption(
                    Bucket=self.bucket_name
                )
                encryption_enabled = True
            except:
                encryption_enabled = False
            
            return {
                "success": True,
                "bucket_name": self.bucket_name,
                "region": location_response.get('LocationConstraint', 'us-east-1'),
                "versioning": versioning_status,
                "encryption_enabled": encryption_enabled
            }
            
        except Exception as e:
            logger.error(f"Failed to get bucket info: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }


# Singleton instance
s3_service = S3Service()
