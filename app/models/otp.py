from datetime import datetime, timedelta
from typing import Optional
from pydantic import BaseModel, Field
from pynamodb.models import Model
from pynamodb.attributes import UnicodeAttribute, UTCDateTimeAttribute, NumberAttribute
from app.core.config import settings
import uuid
import random


class OTPVerification(BaseModel):
    otp_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    email: str
    otp_code: str
    user_id: str
    expires_at: datetime
    created_at: datetime = Field(default_factory=datetime.utcnow)
    attempts: int = 0
    is_used: bool = False
    
    class Config:
        use_enum_values = True


class OTPTable(Model):
    
    class Meta:
        table_name = "otp_verifications"
        region = settings.dynamodb_region
        if settings.dynamodb_endpoint_url:
            host = settings.dynamodb_endpoint_url
        if settings.aws_access_key_id and settings.aws_secret_access_key:
            aws_access_key_id = settings.aws_access_key_id
            aws_secret_access_key = settings.aws_secret_access_key

    otp_id = UnicodeAttribute(hash_key=True)
    email = UnicodeAttribute()
    otp_code = UnicodeAttribute()
    user_id = UnicodeAttribute()
    expires_at = UTCDateTimeAttribute()
    created_at = UTCDateTimeAttribute()
    attempts = NumberAttribute(default=0)
    is_used = UnicodeAttribute(default="false")  # DynamoDB doesn't have native boolean, use string


def generate_otp_code() -> str:
    """Generate a 6-digit OTP code"""
    return f"{random.randint(100000, 999999)}"


def create_otp_expiry() -> datetime:
    """Create OTP expiry time (15 minutes from now)"""
    return datetime.utcnow() + timedelta(minutes=15)