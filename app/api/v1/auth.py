from fastapi import APIRouter, HTTPException, status, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
from datetime import datetime
import logging

from app.schemas.user import (
    UserRegisterRequest, UserLoginRequest, UserResponse, 
    TokenResponse, RefreshTokenRequest, UserUpdateRequest,
    OTPVerificationRequest, ResendOTPRequest
)
from app.services.auth_service import AuthService
from app.services.email import email_service
from app.core.security import verify_token
from app.models.user import User

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])

security = HTTPBearer()

auth_service = AuthService()


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> User:
    """Get current authenticated user"""
    try:
        token = credentials.credentials
        payload = verify_token(token, "access")
        user_id = payload.get("user_id")
        
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        
        # Get user from database
        user = auth_service.user_repo.get_user_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )
        
        return user
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting current user: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials"
        )


@router.post("/register", response_model=dict, status_code=status.HTTP_201_CREATED,
            summary="Đăng ký tài khoản mới",
            description="Tạo tài khoản người dùng mới với email và mật khẩu. Gửi OTP qua email để xác thực.")
async def register(request: Request, user_data: UserRegisterRequest):
    """Register a new user account"""
    try:
        logger.info(f"Registration attempt for email: {user_data.email}")
        
        success, message = await auth_service.register_user(user_data)
        
        if not success:
            logger.warning(f"Registration failed for {user_data.email}: {message}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=message
            )
        
        logger.info(f"User registered successfully: {user_data.email}")
        return {
            "message": message,
            "email": user_data.email,
            "status": "pending_verification"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in register: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during registration"
        )


@router.post("/login", response_model=TokenResponse,
            summary="Đăng nhập",
            description="Đăng nhập bằng email và mật khẩu. Trả về access token và refresh token.")
async def login(request: Request, login_data: UserLoginRequest):
    """
    Authenticate user and return access tokens
    
    - **email**: User's email address
    - **password**: User's password
    """
    try:
        logger.info(f"Login attempt for email: {login_data.email}")
        
        user, message = await auth_service.authenticate_user(login_data)
        
        if not user:
            logger.warning(f"Login failed for {login_data.email}: {message}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=message
            )
        
        token_response = await auth_service.create_user_session(user)
        
        logger.info(f"User logged in successfully: {user.email}")
        return token_response
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in login: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during login"
        )


@router.post("/logout", response_model=dict,
            summary="Đăng xuất",
            description="Đăng xuất và vô hiệu hóa token hiện tại.")
async def logout(request: Request, current_user: User = Depends(get_current_user)):
    """Logout user and invalidate session"""
    try:
        logger.info(f"Logout request for user: {current_user.user_id}")
        
        success = await auth_service.logout_user(current_user.user_id)
        
        if not success:
            logger.warning(f"Failed to logout user: {current_user.user_id}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to logout"
            )
        
        logger.info(f"User logged out successfully: {current_user.user_id}")
        return {"message": "Logged out successfully"}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in logout: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during logout"
        )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(request: Request, refresh_data: RefreshTokenRequest):
    """Refresh access token using refresh token"""
    try:
        logger.info("Token refresh attempt")
        
        token_response = await auth_service.refresh_access_token(refresh_data.refresh_token)
        
        logger.info("Token refreshed successfully")
        return token_response
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in refresh_token: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during token refresh"
        )


@router.get("/me", response_model=UserResponse,
           summary="Lấy thông tin cá nhân",
           description="Lấy thông tin chi tiết của người dùng hiện tại.")
async def get_current_user_info(request: Request, current_user: User = Depends(get_current_user)):
    """Get current user information"""
    try:
        logger.info(f"User info request for: {current_user.user_id}")
        
        return UserResponse(
            user_id=current_user.user_id,
            email=current_user.email,
            full_name=current_user.full_name,
            phone=current_user.phone,
            role=current_user.role,
            status=current_user.status,
            email_verified=current_user.email_verified,
            created_at=current_user.created_at,
            updated_at=current_user.updated_at,
            last_login=current_user.last_login
        )
    
    except Exception as e:
        logger.error(f"Unexpected error in get_current_user_info: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.put("/me", response_model=UserResponse)
async def update_current_user(
    request: Request, 
    user_update: UserUpdateRequest,
    current_user: User = Depends(get_current_user)
):
    """Update current user information"""
    try:
        logger.info(f"User update request for: {current_user.user_id}")
        
        update_data = {}
        if user_update.full_name is not None:
            update_data["full_name"] = user_update.full_name
        if user_update.phone is not None:
            update_data["phone"] = user_update.phone
        
        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No fields to update"
            )
        
        success = auth_service.user_repo.update_user(current_user.user_id, update_data)
        
        if not success:
            logger.warning(f"Failed to update user: {current_user.user_id}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update user"
            )
        
        updated_user = auth_service.user_repo.get_user_by_id(current_user.user_id)
        
        logger.info(f"User updated successfully: {current_user.user_id}")
        return UserResponse(
            user_id=updated_user.user_id,
            email=updated_user.email,
            full_name=updated_user.full_name,
            phone=updated_user.phone,
            role=updated_user.role,
            status=updated_user.status,
            email_verified=updated_user.email_verified,
            created_at=updated_user.created_at,
            last_login=updated_user.last_login
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in update_current_user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during user update"
        )


@router.post("/verify-otp", response_model=dict)
async def verify_otp(request: Request, otp_data: OTPVerificationRequest):
    """
    Verify OTP code để kích hoạt tài khoản
    
    - **email**: Email của user
    - **otp_code**: Mã OTP 6 số
    """
    try:
        logger.info(f"OTP verification attempt for email: {otp_data.email}")
        
        success, message = await auth_service.verify_otp_code(otp_data.email, otp_data.otp_code)
        
        if not success:
            logger.warning(f"OTP verification failed for {otp_data.email}: {message}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=message
            )
        
        logger.info(f"OTP verified successfully for: {otp_data.email}")
        return {
            "message": message,
            "email": otp_data.email,
            "status": "verified"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in verify_otp: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during OTP verification"
        )


@router.post("/resend-otp", response_model=dict)
async def resend_otp(request: Request, resend_data: ResendOTPRequest):
    """
    Gửi lại mã OTP verification
    
    - **email**: Email của user cần gửi lại OTP
    """
    try:
        logger.info(f"Resend OTP attempt for email: {resend_data.email}")
        
        success, message = await auth_service.resend_otp_code(resend_data.email)
        
        if not success:
            logger.warning(f"Resend OTP failed for {resend_data.email}: {message}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=message
            )
        
        logger.info(f"OTP resent successfully for: {resend_data.email}")
        return {
            "message": message,
            "email": resend_data.email
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in resend_otp: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during OTP resend"
        )


@router.post("/forgot-password", response_model=dict)
async def forgot_password(request: Request, email: str):
    """Send password reset email to user"""
    try:
        logger.info(f"Forgot password request for: {email}")
        
        # Tìm user theo email
        user = auth_service.user_repo.get_user_by_email(email)
        if not user:
            # Không tiết lộ thông tin về user tồn tại hay không
            logger.info(f"Password reset requested for non-existent email: {email}")
            return {
                "message": "If the email exists, a password reset link has been sent"
            }
        
        # Gửi password reset email
        result = await email_service.send_password_reset_email(email, user.user_id)
        
        if not result["success"]:
            logger.warning(f"Failed to send password reset email: {result['error']}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to send password reset email"
            )
        
        logger.info(f"Password reset email sent successfully to: {email}")
        return {
            "message": "If the email exists, a password reset link has been sent",
            "email": email
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in forgot_password: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during password reset"
        )


@router.post("/reset-password", response_model=dict)
async def reset_password(request: Request, token: str, new_password: str):
    """Reset user password with reset token"""
    try:
        logger.info("Password reset attempt")
        
        # Verify reset token
        result = await email_service.verify_email_token(token)
        
        if not result["success"]:
            logger.warning(f"Password reset failed: {result['error']}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["error"]
            )
        
        user_id = result["user_id"]
        
        # Validate new password
        if len(new_password) < settings.password_min_length:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Password must be at least {settings.password_min_length} characters long"
            )
        
        # Update user password
        success = await auth_service.update_user_password(user_id, new_password)
        
        if not success:
            logger.warning(f"Failed to update password for user: {user_id}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update password"
            )
        
        logger.info(f"Password reset successfully for user: {user_id}")
        return {
            "message": "Password reset successfully"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in reset_password: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during password reset"
        )
