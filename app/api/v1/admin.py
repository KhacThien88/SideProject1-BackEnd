"""
Admin API Endpoints
For testing and development only
"""
from fastapi import APIRouter, HTTPException, status, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import List, Optional
import logging

from app.core.security import verify_token
from app.models.user import User, UserRole
from app.services.auth_service import AuthService
from app.schemas.user import UserResponse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["Admin"])
security = HTTPBearer()
auth_service = AuthService()


def get_admin_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> User:
    """Verify admin user"""
    try:
        token = credentials.credentials
        payload = verify_token(token, "access")
        user_id = payload.get("user_id")
        
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        
        user = auth_service.user_repo.get_user_by_id(user_id)
        if not user or user.role != UserRole.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required"
            )
        
        return user
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error verifying admin user: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate admin credentials"
        )


@router.get("/users", response_model=List[UserResponse],
           summary="List All Users",
           description="Get a list of all users in the system. Admin only.")
async def list_all_users(
    request: Request,
    admin_user: User = Depends(get_admin_user)
):
    """List all users (Admin only)"""
    try:
        logger.info(f"Admin {admin_user.user_id} requesting user list")
        
        # Scan all users from DynamoDB
        from app.models.user import UserTable
        users = []
        
        for user_item in UserTable.scan():
            user = auth_service.user_repo._table_to_user(user_item)
            users.append(UserResponse(
                user_id=user.user_id,
                email=user.email,
                full_name=user.full_name,
                phone=user.phone,
                role=user.role,
                status=user.status,
                email_verified=user.email_verified,
                created_at=user.created_at,
                updated_at=user.updated_at,
                last_login=user.last_login
            ))
        
        logger.info(f"Retrieved {len(users)} users")
        return users
    
    except Exception as e:
        logger.error(f"Error listing users: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve users"
        )


@router.delete("/users/{user_id}")
async def delete_user_by_id(
    user_id: str,
    request: Request,
    admin_user: User = Depends(get_admin_user)
):
    """Delete user by ID (Admin only - For testing purposes)"""
    try:
        logger.info(f"Admin {admin_user.user_id} requesting deletion of user {user_id}")
        
        # Check if user exists
        target_user = auth_service.user_repo.get_user_by_id(user_id)
        if not target_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Prevent admin from deleting themselves
        if user_id == admin_user.user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete your own account"
            )
        
        # Delete user sessions first
        success_sessions = auth_service.user_repo.deactivate_user_sessions(user_id)
        if not success_sessions:
            logger.warning(f"Failed to deactivate sessions for user {user_id}")
        
        # Delete user
        success = auth_service.user_repo.delete_user(user_id)
        
        if not success:
            logger.error(f"Failed to delete user {user_id}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete user"
            )
        
        logger.info(f"User {user_id} ({target_user.email}) deleted successfully by admin {admin_user.user_id}")
        return {
            "message": f"User {target_user.email} deleted successfully",
            "deleted_user_id": user_id,
            "deleted_email": target_user.email
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete user"
        )


@router.delete("/users/by-email/{email}")
async def delete_user_by_email(
    email: str,
    request: Request,
    admin_user: User = Depends(get_admin_user)
):
    """Delete user by email (Admin only - For testing purposes)"""
    try:
        logger.info(f"Admin {admin_user.user_id} requesting deletion of user with email {email}")
        
        # Find user by email
        target_user = auth_service.user_repo.get_user_by_email(email)
        if not target_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Prevent admin from deleting themselves
        if target_user.user_id == admin_user.user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete your own account"
            )
        
        # Delete user sessions first
        success_sessions = auth_service.user_repo.deactivate_user_sessions(target_user.user_id)
        if not success_sessions:
            logger.warning(f"Failed to deactivate sessions for user {target_user.user_id}")
        
        # Delete user
        success = auth_service.user_repo.delete_user(target_user.user_id)
        
        if not success:
            logger.error(f"Failed to delete user {target_user.user_id}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete user"
            )
        
        logger.info(f"User {target_user.user_id} ({email}) deleted successfully by admin {admin_user.user_id}")
        return {
            "message": f"User {email} deleted successfully",
            "deleted_user_id": target_user.user_id,
            "deleted_email": email
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting user with email {email}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete user"
        )