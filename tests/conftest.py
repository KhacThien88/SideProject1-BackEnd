import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import os
import sys

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.main import app


@pytest.fixture
def client():
    """Create test client"""
    return TestClient(app)


@pytest.fixture
def mock_user():
    """Mock user object for testing"""
    from app.models.user import User, UserRole, UserStatus
    from datetime import datetime
    
    return User(
        user_id="test-user-id",
        email="test@example.com",
        password_hash="hashed_password",
        full_name="Test User",
        phone="+1234567890",
        role=UserRole.CANDIDATE,
        status=UserStatus.ACTIVE,
        email_verified=True,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        last_login=datetime.utcnow()
    )


@pytest.fixture
def mock_user_data():
    """Mock user registration data"""
    return {
        "email": "test@example.com",
        "password": "TestPassword123!",
        "confirm_password": "TestPassword123!",
        "full_name": "Test User",
        "phone": "+1234567890",
        "role": "candidate"
    }


@pytest.fixture
def mock_login_data():
    """Mock user login data"""
    return {
        "email": "test@example.com",
        "password": "TestPassword123!"
    }


@pytest.fixture
def mock_token_response():
    """Mock token response"""
    return {
        "access_token": "test-access-token",
        "refresh_token": "test-refresh-token",
        "token_type": "bearer",
        "expires_in": 1800
    }


@pytest.fixture
def mock_auth_headers():
    """Mock authorization headers"""
    return {"Authorization": "Bearer test-access-token"}


@pytest.fixture(autouse=True)
def mock_user_repository():
    """Provide an in-memory UserRepository replacement for tests (no DynamoDB)."""
    from app.models.user import User, UserSession

    class InMemoryUserRepository:
        def __init__(self):
            self.users_by_id = {}
            self.users_by_email = {}
            self.sessions = {}

        def create_user(self, user: User) -> bool:
            if user.email in self.users_by_email:
                return False
            self.users_by_id[user.user_id] = user
            self.users_by_email[user.email] = user
            return True

        def get_user_by_id(self, user_id: str):
            return self.users_by_id.get(user_id)

        def get_user_by_email(self, email: str):
            return self.users_by_email.get(email)

        def update_user(self, user_id: str, update_data: dict) -> bool:
            user = self.users_by_id.get(user_id)
            if not user:
                return False
            for k, v in update_data.items():
                setattr(user, k, v)
            self.users_by_id[user_id] = user
            self.users_by_email[user.email] = user
            return True

        def delete_user(self, user_id: str) -> bool:
            user = self.users_by_id.pop(user_id, None)
            if user:
                self.users_by_email.pop(user.email, None)
                return True
            return False

        def email_exists(self, email: str) -> bool:
            return email in self.users_by_email

        def create_session(self, session: UserSession) -> bool:
            self.sessions[session.session_id] = session
            return True

        def get_session(self, session_id: str):
            return self.sessions.get(session_id)

        def get_user_sessions(self, user_id: str):
            return [s for s in self.sessions.values() if s.user_id == user_id and s.is_active]

        def deactivate_session(self, session_id: str) -> bool:
            s = self.sessions.get(session_id)
            if not s:
                return False
            s.is_active = False
            self.sessions[session_id] = s
            return True

        def deactivate_user_sessions(self, user_id: str) -> bool:
            any_changed = False
            for s in self.sessions.values():
                if s.user_id == user_id:
                    s.is_active = False
                    any_changed = True
            return any_changed

    repo = InMemoryUserRepository()

    # Patch the repository class so AuthService() uses in-memory repo
    with patch('app.repositories.user.UserRepository', return_value=repo):
        yield repo


# Remove autouse security mocking to not affect JWT unit tests.


@pytest.fixture
def sample_register_request():
    """Sample valid registration request"""
    return {
        "email": "newuser@example.com",
        "password": "SecurePassword123!",
        "confirm_password": "SecurePassword123!",
        "full_name": "New User",
        "phone": "+1234567890",
        "role": "candidate"
    }


@pytest.fixture
def sample_login_request():
    """Sample valid login request"""
    return {
        "email": "user@example.com",
        "password": "UserPassword123!"
    }


@pytest.fixture
def sample_user_response():
    """Sample user response"""
    return {
        "user_id": "user-123",
        "email": "user@example.com",
        "full_name": "Test User",
        "phone": "+1234567890",
        "role": "candidate",
        "status": "active",
        "email_verified": True,
        "created_at": "2024-01-01T00:00:00Z",
        "last_login": "2024-01-01T12:00:00Z"
    }
