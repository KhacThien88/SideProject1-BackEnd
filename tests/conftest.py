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
def mock_database():
    """Mock database operations"""
    with patch('app.core.database.db_client') as mock_db:
        # Configure mock database responses
        mock_db.put_item.return_value = True
        mock_db.get_item.return_value = None
        mock_db.update_item.return_value = True
        mock_db.delete_item.return_value = True
        mock_db.query.return_value = []
        mock_db.scan.return_value = []
        
        yield mock_db


@pytest.fixture(autouse=True)
def mock_auth_service():
    """Mock authentication service"""
    with patch('app.services.auth_service.AuthService') as mock_service:
        # Configure mock service methods
        mock_service.return_value.register_user.return_value = (True, "User registered successfully")
        mock_service.return_value.authenticate_user.return_value = (None, "Invalid credentials")
        mock_service.return_value.create_user_session.return_value = mock_token_response()
        mock_service.return_value.refresh_access_token.return_value = mock_token_response()
        mock_service.return_value.logout_user.return_value = True
        mock_service.return_value.get_current_user.return_value = None
        mock_service.return_value.verify_email.return_value = (True, "Email verified successfully")
        
        yield mock_service


@pytest.fixture(autouse=True)
def mock_security():
    """Mock security functions"""
    with patch('app.core.security.verify_token') as mock_verify:
        mock_verify.return_value = {"user_id": "test-user-id", "email": "test@example.com"}
        yield mock_verify


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
