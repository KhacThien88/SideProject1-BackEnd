from fastapi import APIRouter, HTTPException, status, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
from datetime import datetime
import logging

from app.schemas.user import (
    UserRegisterRequest, UserLoginRequest, UserResponse, 
    TokenResponse, RefreshTokenRequest, UserUpdateRequest
)
from app.services.auth_service import AuthService
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


@router.post("/register", response_model=dict, status_code=status.HTTP_201_CREATED)
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


@router.post("/login", response_model=TokenResponse)
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


@router.post("/logout", response_model=dict)
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


@router.get("/me", response_model=UserResponse)
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


@router.post("/verify-email", response_model=dict)
async def verify_email(request: Request, token: str):
    """Verify user email with verification token"""
    try:
        logger.info("Email verification attempt")
        
        success, message = await auth_service.verify_email(token)
        
        if not success:
            logger.warning(f"Email verification failed: {message}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=message
            )
        
        logger.info("Email verified successfully")
        return {"message": message}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in verify_email: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during email verification"
        )
