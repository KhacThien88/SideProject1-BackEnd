from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional
from enum import Enum
from datetime import datetime


class UserRole(str, Enum):
    CANDIDATE = "candidate"
    RECRUITER = "recruiter"
    ADMIN = "admin"


class UserStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING_VERIFICATION = "pending_verification"
    SUSPENDED = "suspended"


class UserRegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    confirm_password: str
    full_name: str = Field(..., min_length=2, max_length=100)
    phone: Optional[str] = Field(None, pattern=r'^[0-9+\-\s()]+$')
    role: UserRole = UserRole.CANDIDATE

    @validator('confirm_password')
    def passwords_match(cls, v, values):
        if 'password' in values and v != values['password']:
            raise ValueError('Passwords do not match')
        return v


class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    user_id: str
    email: EmailStr
    full_name: str
    phone: Optional[str]
    role: UserRole
    status: UserStatus
    email_verified: bool
    created_at: datetime
    updated_at: datetime
    last_login: Optional[datetime]
    google_id: Optional[str]
    auth_provider: str

    class Config:
        from_attributes = True


class UserUpdateRequest(BaseModel):
    full_name: Optional[str] = Field(None, min_length=2, max_length=100)
    phone: Optional[str] = Field(None, pattern=r'^[0-9+\-\s()]+$')


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class OTPVerificationRequest(BaseModel):
    email: EmailStr
    otp_code: str = Field(..., min_length=6, max_length=6, pattern=r'^\d{6}$')


class ResendOTPRequest(BaseModel):
    email: EmailStr


class GoogleAuthRequest(BaseModel):
    google_token: str


class GoogleAuthResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse
    is_new_user: bool
