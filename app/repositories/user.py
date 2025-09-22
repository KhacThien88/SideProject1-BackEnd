from typing import Optional, List
from datetime import datetime
from app.core.database import db_client
from app.models.user import User, UserSession
from app.schemas.user import UserRole, UserStatus
import json


class UserRepository:
    def __init__(self):
        self.table_name = "users"
        self.sessions_table_name = "user_sessions"

    def create_user(self, user: User) -> bool:
        """Create a new user"""
        try:
            user_dict = user.dict()
            user_dict['created_at'] = user.created_at.isoformat()
            user_dict['updated_at'] = user.updated_at.isoformat()
            if user.last_login:
                user_dict['last_login'] = user.last_login.isoformat()
            
            return db_client.put_item(self.table_name, user_dict)
        except Exception as e:
            print(f"Error creating user: {e}")
            return False

    def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Get user by ID"""
        try:
            item = db_client.get_item(self.table_name, {"user_id": user_id})
            if item:
                return self._dict_to_user(item)
            return None
        except Exception as e:
            print(f"Error getting user by ID: {e}")
            return None

    def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email"""
        try:
            # Query using GSI on email
            items = db_client.query(
                self.table_name,
                "email = :email",
                {":email": email}
            )
            if items:
                return self._dict_to_user(items[0])
            return None
        except Exception as e:
            print(f"Error getting user by email: {e}")
            return None

    def update_user(self, user_id: str, update_data: dict) -> bool:
        """Update user information"""
        try:
            update_expression = "SET updated_at = :updated_at"
            expression_values = {":updated_at": datetime.utcnow().isoformat()}
            
            for key, value in update_data.items():
                if key not in ['user_id', 'created_at']:  # Don't update these fields
                    update_expression += f", {key} = :{key}"
                    if isinstance(value, datetime):
                        expression_values[f":{key}"] = value.isoformat()
                    else:
                        expression_values[f":{key}"] = value
            
            return db_client.update_item(
                self.table_name,
                {"user_id": user_id},
                update_expression,
                expression_values
            )
        except Exception as e:
            print(f"Error updating user: {e}")
            return False

    def delete_user(self, user_id: str) -> bool:
        """Delete user"""
        try:
            return db_client.delete_item(self.table_name, {"user_id": user_id})
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
            session_dict = session.dict()
            session_dict['created_at'] = session.created_at.isoformat()
            session_dict['expires_at'] = session.expires_at.isoformat()
            
            return db_client.put_item(self.sessions_table_name, session_dict)
        except Exception as e:
            print(f"Error creating session: {e}")
            return False

    def get_session(self, session_id: str) -> Optional[UserSession]:
        """Get user session by session ID"""
        try:
            item = db_client.get_item(self.sessions_table_name, {"session_id": session_id})
            if item:
                return self._dict_to_session(item)
            return None
        except Exception as e:
            print(f"Error getting session: {e}")
            return None

    def get_user_sessions(self, user_id: str) -> List[UserSession]:
        """Get all active sessions for a user"""
        try:
            items = db_client.query(
                self.sessions_table_name,
                "user_id = :user_id",
                {":user_id": user_id}
            )
            return [self._dict_to_session(item) for item in items if item.get('is_active', True)]
        except Exception as e:
            print(f"Error getting user sessions: {e}")
            return []

    def deactivate_session(self, session_id: str) -> bool:
        """Deactivate a session"""
        try:
            return db_client.update_item(
                self.sessions_table_name,
                {"session_id": session_id},
                "SET is_active = :is_active",
                {":is_active": False}
            )
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

    def _dict_to_user(self, item: dict) -> User:
        """Convert dictionary to User object"""
        # Convert datetime strings back to datetime objects
        if 'created_at' in item and isinstance(item['created_at'], str):
            item['created_at'] = datetime.fromisoformat(item['created_at'].replace('Z', '+00:00'))
        if 'updated_at' in item and isinstance(item['updated_at'], str):
            item['updated_at'] = datetime.fromisoformat(item['updated_at'].replace('Z', '+00:00'))
        if 'last_login' in item and isinstance(item['last_login'], str):
            item['last_login'] = datetime.fromisoformat(item['last_login'].replace('Z', '+00:00'))
        
        return User(**item)

    def _dict_to_session(self, item: dict) -> UserSession:
        """Convert dictionary to UserSession object"""
        # Convert datetime strings back to datetime objects
        if 'created_at' in item and isinstance(item['created_at'], str):
            item['created_at'] = datetime.fromisoformat(item['created_at'].replace('Z', '+00:00'))
        if 'expires_at' in item and isinstance(item['expires_at'], str):
            item['expires_at'] = datetime.fromisoformat(item['expires_at'].replace('Z', '+00:00'))
        
        return UserSession(**item)
