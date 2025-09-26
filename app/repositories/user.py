from typing import Optional, List
from datetime import datetime
from app.core.database import db_client
from app.models.user import User, UserSession, UserTable, UserSessionTable
from app.schemas.user import UserRole, UserStatus
import json


class UserRepository:
    def __init__(self):
        self.table_name = "users"
        self.sessions_table_name = "user_sessions"

    def create_user(self, user: User) -> bool:
        """Create a new user"""
        try:
            item = UserTable(
                user_id=user.user_id,
                email=user.email,
                password_hash=user.password_hash,
                full_name=user.full_name,
                phone=user.phone or "",
                role=user.role,
                status=user.status,
                email_verified=user.email_verified,
                created_at=user.created_at,
                updated_at=user.updated_at,
                last_login=user.last_login
            )
            item.save()
            return True
        except Exception as e:
            print(f"Error creating user: {e}")
            return False

    def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Get user by ID"""
        try:
            item = UserTable.get(user_id)
            if item:
                return self._table_to_user(item)
            return None
        except Exception as e:
            print(f"Error getting user by ID: {e}")
            return None

    def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email"""
        try:
            # Query using GSI on email
            # Query by GSI
            for item in UserTable.email_index.query(email):
                return self._table_to_user(item)
            return None
        except Exception as e:
            print(f"Error getting user by email: {e}")
            return None

    def update_user(self, user_id: str, update_data: dict) -> bool:
        """Update user information"""
        try:
            item = UserTable.get(user_id)
            for key, value in update_data.items():
                setattr(item, key, value)
            item.updated_at = datetime.utcnow()
            item.save()
            return True
        except Exception as e:
            print(f"Error updating user: {e}")
            return False

    def delete_user(self, user_id: str) -> bool:
        """Delete user"""
        try:
            item = UserTable.get(user_id)
            item.delete()
            return True
        except Exception as e:
            print(f"Error deleting user: {e}")
            return False

    def email_exists(self, email: str) -> bool:
        """Check if email already exists"""
        user = self.get_user_by_email(email)
        return user is not None

    def create_session(self, session: UserSession) -> bool:
        """Create user session"""
        try:
            item = UserSessionTable(
                session_id=session.session_id,
                user_id=session.user_id,
                access_token=session.access_token,
                refresh_token=session.refresh_token,
                expires_at=session.expires_at,
                created_at=session.created_at,
                is_active=session.is_active
            )
            item.save()
            return True
        except Exception as e:
            print(f"Error creating session: {e}")
            return False

    def get_session(self, session_id: str) -> Optional[UserSession]:
        """Get user session by session ID"""
        try:
            item = UserSessionTable.get(session_id)
            if item:
                return self._table_to_session(item)
            return None
        except Exception as e:
            print(f"Error getting session: {e}")
            return None

    def get_user_sessions(self, user_id: str) -> List[UserSession]:
        """Get all active sessions for a user"""
        try:
            # Query by GSI
            items = [self._table_to_session(it) for it in UserSessionTable.user_id_index.query(user_id)]
            return [it for it in items if it.is_active]
        except Exception as e:
            print(f"Error getting user sessions: {e}")
            return []

    def deactivate_session(self, session_id: str) -> bool:
        """Deactivate a session"""
        try:
            item = UserSessionTable.get(session_id)
            item.is_active = False
            item.save()
            return True
        except Exception as e:
            print(f"Error deactivating session: {e}")
            return False

    def deactivate_user_sessions(self, user_id: str) -> bool:
        """Deactivate all sessions for a user"""
        try:
            sessions = self.get_user_sessions(user_id)
            for session in sessions:
                self.deactivate_session(session.session_id)
            return True
        except Exception as e:
            print(f"Error deactivating user sessions: {e}")
            return False

    def _table_to_user(self, item: UserTable) -> User:
        return User(
            user_id=item.user_id,
            email=item.email,
            password_hash=item.password_hash,
            full_name=item.full_name,
            phone=item.phone if item.phone else None,
            role=item.role,
            status=item.status,
            email_verified=bool(item.email_verified),
            created_at=item.created_at,
            updated_at=item.updated_at,
            last_login=item.last_login
        )

    def _table_to_session(self, item: UserSessionTable) -> UserSession:
        return UserSession(
            session_id=item.session_id,
            user_id=item.user_id,
            access_token=item.access_token,
            refresh_token=item.refresh_token,
            expires_at=item.expires_at,
            created_at=item.created_at,
            is_active=bool(item.is_active)
        )
