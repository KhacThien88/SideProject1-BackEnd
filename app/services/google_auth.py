from typing import Optional, Tuple, Dict, Any
from datetime import datetime
import httpx
import logging
from google.oauth2 import id_token
from google.auth.transport import requests
from google.auth.exceptions import GoogleAuthError

from app.core.config import settings
from app.models.user import User, UserRole, UserStatus
from app.repositories.user import UserRepository
from app.services.auth_service import AuthService
from app.schemas.user import UserResponse

logger = logging.getLogger(__name__)


class GoogleAuthService:
    def __init__(self):
        self.user_repo = UserRepository()
        self.auth_service = AuthService()
    
    async def verify_google_token(self, google_token: str) -> Tuple[bool, Optional[Dict[str, Any]], str]:
        """
        Verify Google ID token and extract user information
        
        Args:
            google_token: Google ID token from frontend
            
        Returns:
            Tuple of (success, user_info, message)
        """
        try:
            if not settings.google_client_id:
                return False, None, "Google OAuth not configured"
            
            # Verify the token
            idinfo = id_token.verify_oauth2_token(
                google_token, 
                requests.Request(), 
                settings.google_client_id
            )
            
            # Extract user information
            user_info = {
                "google_id": idinfo.get("sub"),
                "email": idinfo.get("email"),
                "full_name": idinfo.get("name"),
                "email_verified": idinfo.get("email_verified", False),
                "picture": idinfo.get("picture")
            }
            
            # Validate required fields
            if not user_info["google_id"] or not user_info["email"]:
                return False, None, "Invalid Google token: missing required fields"
            
            return True, user_info, "Token verified successfully"
            
        except GoogleAuthError as e:
            logger.error(f"Google auth error: {e}")
            return False, None, "Invalid Google token"
        except Exception as e:
            logger.error(f"Error verifying Google token: {e}")
            return False, None, "Error verifying Google token"
    
    async def authenticate_or_create_user(self, google_token: str) -> Tuple[Optional[User], bool, str]:
        """
        Authenticate existing user or create new user from Google token
        
        Args:
            google_token: Google ID token from frontend
            
        Returns:
            Tuple of (user, is_new_user, message)
        """
        try:
            # Verify Google token
            success, user_info, message = await self.verify_google_token(google_token)
            if not success:
                return None, False, message
            
            google_id = user_info["google_id"]
            email = user_info["email"]
            full_name = user_info["full_name"]
            email_verified = user_info["email_verified"]
            
            # Check if user exists by Google ID
            existing_user = self.user_repo.get_user_by_google_id(google_id)
            if existing_user:
                # Update last login
                self.user_repo.update_user(existing_user.user_id, {
                    "last_login": datetime.utcnow()
                })
                return existing_user, False, "User authenticated successfully"
            
            # Check if user exists by email (for account linking)
            existing_user_by_email = self.user_repo.get_user_by_email(email)
            if existing_user_by_email:
                # Link Google account to existing user
                self.user_repo.update_user(existing_user_by_email.user_id, {
                    "google_id": google_id,
                    "auth_provider": "google",
                    "email_verified": True,
                    "status": UserStatus.ACTIVE,
                    "last_login": datetime.utcnow()
                })
                return existing_user_by_email, False, "Google account linked successfully"
            
            # Create new user
            new_user = User(
                email=email,
                password_hash=None,  # No password for Google users
                full_name=full_name,
                phone=None,
                role=UserRole.CANDIDATE,
                status=UserStatus.ACTIVE,
                email_verified=email_verified,
                google_id=google_id,
                auth_provider="google"
            )
            
            if not self.user_repo.create_user(new_user):
                return None, False, "Failed to create user account"
            
            return new_user, True, "User created and authenticated successfully"
            
        except Exception as e:
            logger.error(f"Error in authenticate_or_create_user: {e}")
            return None, False, "Internal server error during Google authentication"
    
    async def get_user_by_google_id(self, google_id: str) -> Optional[User]:
        """Get user by Google ID"""
        try:
            return self.user_repo.get_user_by_google_id(google_id)
        except Exception as e:
            logger.error(f"Error getting user by Google ID: {e}")
            return None


# Global instance
google_auth_service = GoogleAuthService()
