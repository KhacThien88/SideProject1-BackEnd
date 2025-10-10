from datetime import datetime
from typing import Optional, List
from enum import Enum
from pydantic import BaseModel, EmailStr, Field
from pynamodb.models import Model
from pynamodb.attributes import (
    UnicodeAttribute, BooleanAttribute, UTCDateTimeAttribute
)
from pynamodb.indexes import GlobalSecondaryIndex, AllProjection
from app.core.config import settings
import uuid


class UserRole(str, Enum):
    CANDIDATE = "candidate"
    RECRUITER = "recruiter"
    ADMIN = "admin"


class UserStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING_VERIFICATION = "pending_verification"
    SUSPENDED = "suspended"


class User(BaseModel):
    user_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    email: EmailStr
    password_hash: Optional[str] = None
    full_name: str
    phone: Optional[str] = None
    role: UserRole
    status: UserStatus = UserStatus.PENDING_VERIFICATION
    email_verified: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    last_login: Optional[datetime] = None
    google_id: Optional[str] = None
    auth_provider: str = "local"  # "local" or "google"
    
    class Config:
        use_enum_values = True


class UserSession(BaseModel):
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    access_token: str
    refresh_token: str
    expires_at: datetime
    created_at: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = True
    
    class Config:
        use_enum_values = True


class UserTable(Model):
    
    class Meta:
        table_name = "users"
        region = settings.dynamodb_region
        if settings.dynamodb_endpoint_url:
            host = settings.dynamodb_endpoint_url
        if settings.aws_access_key_id and settings.aws_secret_access_key:
            aws_access_key_id = settings.aws_access_key_id
            aws_secret_access_key = settings.aws_secret_access_key

    class EmailIndex(GlobalSecondaryIndex):
        class Meta:
            index_name = "email-index"
            projection = AllProjection()
            region = settings.dynamodb_region
            read_capacity_units = 1
            write_capacity_units = 1
            if settings.dynamodb_endpoint_url:
                host = settings.dynamodb_endpoint_url
            if settings.aws_access_key_id and settings.aws_secret_access_key:
                aws_access_key_id = settings.aws_access_key_id
                aws_secret_access_key = settings.aws_secret_access_key
        email = UnicodeAttribute(hash_key=True)

    user_id = UnicodeAttribute(hash_key=True)
    email = UnicodeAttribute()
    password_hash = UnicodeAttribute(null=True)
    full_name = UnicodeAttribute()
    phone = UnicodeAttribute(null=True)
    role = UnicodeAttribute()
    status = UnicodeAttribute()
    email_verified = BooleanAttribute(default=False)
    created_at = UTCDateTimeAttribute()
    updated_at = UTCDateTimeAttribute()
    last_login = UTCDateTimeAttribute(null=True)
    google_id = UnicodeAttribute(null=True)
    auth_provider = UnicodeAttribute(default="local")
    email_index = EmailIndex()


class UserSessionTable(Model):
    
    class Meta:
        table_name = "user_sessions"
        region = settings.dynamodb_region
        if settings.dynamodb_endpoint_url:
            host = settings.dynamodb_endpoint_url
        if settings.aws_access_key_id and settings.aws_secret_access_key:
            aws_access_key_id = settings.aws_access_key_id
            aws_secret_access_key = settings.aws_secret_access_key

    class UserIdIndex(GlobalSecondaryIndex):
        class Meta:
            index_name = "user-id-index"
            projection = AllProjection()
            region = settings.dynamodb_region
            read_capacity_units = 1
            write_capacity_units = 1
            if settings.dynamodb_endpoint_url:
                host = settings.dynamodb_endpoint_url
            if settings.aws_access_key_id and settings.aws_secret_access_key:
                aws_access_key_id = settings.aws_access_key_id
                aws_secret_access_key = settings.aws_secret_access_key
        user_id = UnicodeAttribute(hash_key=True)

    session_id = UnicodeAttribute(hash_key=True)
    user_id = UnicodeAttribute()
    access_token = UnicodeAttribute()
    refresh_token = UnicodeAttribute()
    expires_at = UTCDateTimeAttribute()
    created_at = UTCDateTimeAttribute()
    is_active = BooleanAttribute(default=True)
    user_id_index = UserIdIndex()
