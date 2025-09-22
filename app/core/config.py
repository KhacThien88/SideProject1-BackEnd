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
    
    # File Upload
    max_file_size: int = 10485760  # 10MB
    upload_dir: str = "./uploads"
    allowed_file_types: str = "pdf,doc,docx,txt"
    
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
