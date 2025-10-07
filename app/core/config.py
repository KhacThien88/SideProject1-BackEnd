from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    # Application
    app_name: str = "AI Resume Analyzer & Job Match"
    app_version: str = "1.0.0"
    debug: bool = False
    environment: str = "development"
    log_level: str = "INFO"
    
    # Database
    dynamodb_region: str = "us-east-1"
    dynamodb_endpoint_url: Optional[str] = None
    dynamodb_table_prefix: str = "cv-management"
    dynamodb_host: Optional[str] = None
    use_dynamodb: bool = True
    dynamodb_use_local: bool = False
    dynamodb_local_endpoint: Optional[str] = None  # ví dụ: http://localhost:8000
    database_url: Optional[str] = None
    
    # JWT
    secret_key: str = "your-secret-key-change-in-production"
    algorithm: str = "HS256"  # HS256 or RS256
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    # RS256 key paths (optional). If provided and algorithm == RS256, will be used
    jwt_private_key_path: Optional[str] = None
    jwt_public_key_path: Optional[str] = None
    
    # CORS
    cors_origins: str = "http://localhost:3000"
    cors_allow_credentials: bool = True
    
    # Email/SMTP
    smtp_host: Optional[str] = None
    smtp_port: int = 587
    smtp_user: Optional[str] = None
    smtp_pass: Optional[str] = None
    smtp_use_tls: bool = True
    from_email: str = "noreply@example.com"
    
    # AWS (Dùng cho S3/DynamoDB). Hệ thống email hiện dùng SMTP Gmail, không dùng SES
    aws_region: str = "ap-southeast-2"
    aws_access_key_id: Optional[str] = None
    aws_secret_access_key: Optional[str] = None
    # ses_from_email: str = "noreply@example.com"  # Deprecated: email chuyển sang SMTP, không dùng SES
    frontend_url: str = "http://localhost:3000"
    
    # File Upload
    max_file_size: int = 10485760  # 10MB
    upload_dir: str = "./uploads"
    allowed_file_types: str = "pdf,doc,docx,txt"
    
    # S3 Configuration
    s3_bucket_name: str = "my-cv-storage-bucket"
    s3_region: str = "ap-southeast-2"
    s3_access_key_id: Optional[str] = None
    s3_secret_access_key: Optional[str] = None
    s3_endpoint_url: Optional[str] = None
    s3_use_ssl: bool = True
    use_s3: bool = True
    
    # DynamoDB Table Names
    users_table_name: str = "ai-resume-analyzer-users"
    applications_table_name: str = "ai-resume-analyzer-applications"
    jobs_table_name: str = "ai-resume-analyzer-jobs"
    feedback_table_name: str = "ai-resume-analyzer-feedback"
    notifications_table_name: str = "ai-resume-analyzer-notifications"
    cv_uploads_table_name: str = "ai-resume-analyzer-cv-uploads"
    rate_limit_table_name: str = "ai-resume-analyzer-rate-limit"
    email_verification_table_name: str = "ai-resume-analyzer-email-verification"
    cv_storage_table_name: str = "ai-resume-analyzer-cv-storage"
    cv_search_table_name: str = "ai-resume-analyzer-cv-search"
    cv_analytics_table_name: str = "ai-resume-analyzer-cv-analytics"
    
    # Textract Configuration
    textract_sns_topic_arn: Optional[str] = None
    textract_sqs_queue_url: Optional[str] = None
    
    # Security
    password_min_length: int = 8
    password_require_uppercase: bool = True
    password_require_lowercase: bool = True
    password_require_numbers: bool = True
    password_require_special_chars: bool = True
    
    # Rate Limiting
    rate_limit_requests: int = 100
    rate_limit_window: int = 60  # seconds

    # Redis (for token blacklisting)
    redis_url: Optional[str] = "redis://localhost:6379/0"
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
