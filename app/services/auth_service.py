from datetime import datetime, timedelta
from typing import Optional, Tuple
from fastapi import HTTPException, status
from app.core.security import (
    verify_password, get_password_hash, create_access_token, 
    create_refresh_token, verify_token, validate_password_strength,
    generate_verification_token, generate_password_reset_token,
    needs_hash_upgrade
)
from app.repositories.user import UserRepository
from app.models.user import User, UserSession, UserRole, UserStatus
from app.schemas.user import UserRegisterRequest, UserLoginRequest, TokenResponse
from app.core.config import settings
import secrets


class AuthService:
    def __init__(self):
        self.user_repo = UserRepository()

    async def register_user(self, user_data: UserRegisterRequest) -> Tuple[bool, str]:
        """Register a new user"""
        try:
            if user_data.password != user_data.confirm_password:
                return False, "Passwords do not match"

            is_valid, message = validate_password_strength(user_data.password)
            if not is_valid:
                return False, message

            if self.user_repo.email_exists(user_data.email):
                return False, "Email already registered"

            user = User(
                email=user_data.email,
                password_hash=get_password_hash(user_data.password),
                full_name=user_data.full_name,
                phone=user_data.phone,
                role=user_data.role,
                status=UserStatus.PENDING_VERIFICATION
            )

            if not self.user_repo.create_user(user):
                return False, "Failed to create user account"

            # Email verification sẽ bổ sung khi triển khai BE-004

            return True, "User registered successfully"

        except Exception as e:
            print(f"Error in register_user: {e}")
            return False, "Internal server error during registration"

    async def authenticate_user(self, login_data: UserLoginRequest) -> Tuple[Optional[User], str]:
        """Authenticate user login"""
        try:
            user = self.user_repo.get_user_by_email(login_data.email)
            if not user:
                return None, "Invalid email or password"

            if user.status != UserStatus.ACTIVE:
                if user.status == UserStatus.PENDING_VERIFICATION:
                    return None, "Please verify your email before logging in"
                elif user.status == UserStatus.SUSPENDED:
                    return None, "Your account has been suspended"
                else:
                    return None, "Account is not active"

            if not verify_password(login_data.password, user.password_hash):
                return None, "Invalid email or password"

            try:
                if needs_hash_upgrade(user.password_hash):
                    self.user_repo.update_user(user.user_id, {"password_hash": get_password_hash(login_data.password)})
            except Exception:
                pass

            self.user_repo.update_user(user.user_id, {"last_login": datetime.utcnow()})

            return user, "Login successful"

        except Exception as e:
            print(f"Error in authenticate_user: {e}")
            return None, "Internal server error during authentication"

    async def create_user_session(self, user: User) -> TokenResponse:
        """Create user session with tokens"""
        try:
            # Create access token
            access_token_data = {
                "sub": user.user_id,
                "email": user.email,
                "role": user.role,
                "user_id": user.user_id
            }
            access_token = create_access_token(access_token_data)

            # Create refresh token
            refresh_token_data = {
                "sub": user.user_id,
                "email": user.email,
                "user_id": user.user_id
            }
            refresh_token = create_refresh_token(refresh_token_data)

            # Create session
            session = UserSession(
                user_id=user.user_id,
                access_token=access_token,
                refresh_token=refresh_token,
                expires_at=datetime.utcnow() + timedelta(days=settings.refresh_token_expire_days)
            )

            # Save session to database
            if not self.user_repo.create_session(session):
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to create session"
                )

            return TokenResponse(
                access_token=access_token,
                refresh_token=refresh_token,
                expires_in=settings.access_token_expire_minutes * 60
            )

        except Exception as e:
            print(f"Error in create_user_session: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create user session"
            )

    async def refresh_access_token(self, refresh_token: str) -> TokenResponse:
        """Refresh access token using refresh token with rotation.

        - Verifies refresh token
        - Blacklists old refresh token jti
        - Issues new refresh token (rotation)
        - Issues new access token
        """
        try:
            # Verify refresh token
            payload = verify_token(refresh_token, "refresh")
            user_id = payload.get("user_id")

            if not user_id:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid refresh token"
                )

            # Get user
            user = self.user_repo.get_user_by_id(user_id)
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User not found"
                )

            # Check if user is still active
            if user.status != UserStatus.ACTIVE:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User account is not active"
                )

            # Create new access token
            access_token_data = {
                "sub": user.user_id,
                "email": user.email,
                "role": user.role,
                "user_id": user.user_id
            }
            access_token = create_access_token(access_token_data)

            # Rotation: issue new refresh token and (optionally) deactivate existing session
            new_refresh_token = create_refresh_token({
                "sub": user.user_id,
                "email": user.email,
                "user_id": user.user_id
            })

            # Update session store: deactivate old session and create new
            sessions = self.user_repo.get_user_sessions(user_id)
            for session in sessions:
                if session.refresh_token == refresh_token and session.is_active:
                    self.user_repo.deactivate_session(session.session_id)
                    break
            # Create new session
            new_session = UserSession(
                user_id=user.user_id,
                access_token=access_token,
                refresh_token=new_refresh_token,
                expires_at=datetime.utcnow() + timedelta(days=settings.refresh_token_expire_days)
            )
            self.user_repo.create_session(new_session)

            return TokenResponse(
                access_token=access_token,
                refresh_token=new_refresh_token,
                expires_in=settings.access_token_expire_minutes * 60
            )

        except HTTPException:
            raise
        except Exception as e:
            print(f"Error in refresh_access_token: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to refresh token"
            )

    async def logout_user(self, user_id: str, session_id: Optional[str] = None) -> bool:
        """Logout user and invalidate session(s)"""
        try:
            if session_id:
                # Logout specific session
                return self.user_repo.deactivate_session(session_id)
            else:
                # Logout all sessions for user
                return self.user_repo.deactivate_user_sessions(user_id)

        except Exception as e:
            print(f"Error in logout_user: {e}")
            return False

    async def generate_password_reset(self, email: str) -> Tuple[bool, str]:
        """Generate a password reset token for a user (placeholder without email send)."""
        try:
            user = self.user_repo.get_user_by_email(email)
            if not user:
                return False, "User not found"
            token = generate_password_reset_token()
            # Store token and expiry (simple approach on user item)
            self.user_repo.update_user(user.user_id, {
                "reset_token": token,
                "reset_token_expiry": datetime.utcnow() + timedelta(hours=1)
            })
            return True, token
        except Exception as e:
            print(f"Error in generate_password_reset: {e}")
            return False, "Failed to generate reset token"

    async def reset_password(self, token: str, new_password: str) -> Tuple[bool, str]:
        """Reset password using a valid reset token."""
        try:
            # Find user by scanning for reset token (without GSI)
            # In production, add GSI for reset_token
            from app.core.database import db_client
            items = db_client.scan(self.user_repo.table_name)
            match = None
            for it in items:
                if it.get("reset_token") == token:
                    match = it
                    break
            if not match:
                return False, "Invalid or expired reset token"

            # Check expiry
            expiry = match.get("reset_token_expiry")
            if isinstance(expiry, str):
                expiry = datetime.fromisoformat(expiry.replace('Z', '+00:00'))
            if not expiry or expiry < datetime.utcnow():
                return False, "Reset token expired"

            # Validate password policy
            is_valid, message = validate_password_strength(new_password)
            if not is_valid:
                return False, message

            # Update password and clear token
            user_id = match["user_id"]
            self.user_repo.update_user(user_id, {
                "password_hash": get_password_hash(new_password),
                "reset_token": None,
                "reset_token_expiry": None
            })
            return True, "Password has been reset"
        except Exception as e:
            print(f"Error in reset_password: {e}")
            return False, "Failed to reset password"

    async def get_current_user(self, user_id: str) -> Optional[User]:
        """Get current user by ID"""
        try:
            return self.user_repo.get_user_by_id(user_id)
        except Exception as e:
            print(f"Error in get_current_user: {e}")
            return None

    async def verify_email(self, token: str) -> Tuple[bool, str]:
        """Verify user email with token"""
        try:
            # TODO: Implement email verification logic
            # For now, we'll just activate the user
            # In production, you would verify the token and activate the user
            
            # This is a placeholder implementation
            return False, "Email verification not implemented yet"

        except Exception as e:
            print(f"Error in verify_email: {e}")
            return False, "Failed to verify email"
