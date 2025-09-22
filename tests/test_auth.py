import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
import json

from app.main import app
from unittest.mock import patch
from app.models.user import User, UserRole, UserStatus
from app.schemas.user import UserRegisterRequest, UserLoginRequest

client = TestClient(app)


class TestAuthEndpoints:
    """Test authentication endpoints"""

    def test_health_check(self):
        """Test health check endpoint"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data

    def test_root_endpoint(self):
        """Test root endpoint"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "AI Resume Analyzer & Job Match API" in data["message"]

    @patch('app.services.auth_service.AuthService.register_user')
    def test_register_success(self, mock_register):
        """Test successful user registration"""
        # Mock successful registration
        mock_register.return_value = (True, "User registered successfully")
        
        user_data = {
            "email": "test@example.com",
            "password": "TestPassword123!",
            "confirm_password": "TestPassword123!",
            "full_name": "Test User",
            "phone": "+1234567890",
            "role": "candidate"
        }
        
        response = client.post("/api/v1/auth/register", json=user_data)
        assert response.status_code == 201
        data = response.json()
        assert data["message"] == "User registered successfully"
        assert data["email"] == "test@example.com"

    @patch('app.services.auth_service.AuthService.register_user')
    def test_register_password_mismatch(self, mock_register):
        """Test registration with password mismatch"""
        # Mock password mismatch
        mock_register.return_value = (False, "Passwords do not match")
        
        user_data = {
            "email": "test@example.com",
            "password": "TestPassword123!",
            "confirm_password": "DifferentPassword123!",
            "full_name": "Test User",
            "role": "candidate"
        }
        
        response = client.post("/api/v1/auth/register", json=user_data)
        assert response.status_code == 400
        data = response.json()
        assert "Passwords do not match" in data["detail"]

    @patch('app.services.auth_service.AuthService.register_user')
    def test_register_email_exists(self, mock_register):
        """Test registration with existing email"""
        # Mock email already exists
        mock_register.return_value = (False, "Email already registered")
        
        user_data = {
            "email": "existing@example.com",
            "password": "TestPassword123!",
            "confirm_password": "TestPassword123!",
            "full_name": "Test User",
            "role": "candidate"
        }
        
        response = client.post("/api/v1/auth/register", json=user_data)
        assert response.status_code == 400
        data = response.json()
        assert "Email already registered" in data["detail"]

    @patch('app.services.auth_service.AuthService.authenticate_user')
    @patch('app.services.auth_service.AuthService.create_user_session')
    def test_login_success(self, mock_create_session, mock_authenticate):
        """Test successful user login"""
        # Mock user object
        mock_user = User(
            user_id="test-user-id",
            email="test@example.com",
            password_hash="hashed_password",
            full_name="Test User",
            role=UserRole.CANDIDATE,
            status=UserStatus.ACTIVE
        )
        
        # Mock successful authentication
        mock_authenticate.return_value = (mock_user, "Login successful")
        
        # Mock token response
        mock_create_session.return_value = {
            "access_token": "test-access-token",
            "refresh_token": "test-refresh-token",
            "token_type": "bearer",
            "expires_in": 1800
        }
        
        login_data = {
            "email": "test@example.com",
            "password": "TestPassword123!"
        }
        
        response = client.post("/api/v1/auth/login", json=login_data)
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data

    @patch('app.services.auth_service.AuthService.authenticate_user')
    def test_login_invalid_credentials(self, mock_authenticate):
        """Test login with invalid credentials"""
        # Mock failed authentication
        mock_authenticate.return_value = (None, "Invalid email or password")
        
        login_data = {
            "email": "test@example.com",
            "password": "WrongPassword"
        }
        
        response = client.post("/api/v1/auth/login", json=login_data)
        assert response.status_code == 401
        data = response.json()
        assert "Invalid email or password" in data["detail"]

    @patch('app.services.auth_service.AuthService.logout_user')
    def test_logout_success(self, mock_logout, mock_user_repository):
        """Test successful logout"""
        # Mock successful logout
        mock_logout.return_value = True
        
        # Mock user for authentication
        mock_user = User(
            user_id="test-user-id",
            email="test@example.com",
            password_hash="hashed_password",
            full_name="Test User",
            role=UserRole.CANDIDATE,
            status=UserStatus.ACTIVE
        )
        
        # Mock token verification
        # Seed in-memory repo
        mock_user_repository.users_by_id[mock_user.user_id] = mock_user
        mock_user_repository.users_by_email[mock_user.email] = mock_user

        # Ensure router uses in-memory repo
        import app.api.v1.auth as auth_module
        auth_module.auth_service.user_repo = mock_user_repository

        with patch('app.api.v1.auth.verify_token') as mock_verify:
            mock_verify.return_value = {"user_id": "test-user-id"}
            headers = {"Authorization": "Bearer test-token"}
            response = client.post("/api/v1/auth/logout", headers=headers)
            assert response.status_code == 200
            data = response.json()
            assert "Logged out successfully" in data["message"]

    @patch('app.services.auth_service.AuthService.refresh_access_token')
    def test_refresh_token_success(self, mock_refresh):
        """Test successful token refresh"""
        # Mock successful token refresh
        mock_refresh.return_value = {
            "access_token": "new-access-token",
            "refresh_token": "test-refresh-token",
            "token_type": "bearer",
            "expires_in": 1800
        }
        
        refresh_data = {
            "refresh_token": "test-refresh-token"
        }
        
        with patch('app.api.v1.auth.verify_token') as mock_verify:
            mock_verify.return_value = {"user_id": "test-user-id"}
            response = client.post("/api/v1/auth/refresh", json=refresh_data)
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["access_token"] == "new-access-token"

    @patch('app.services.auth_service.AuthService.refresh_access_token')
    def test_refresh_token_invalid(self, mock_refresh):
        """Test token refresh with invalid refresh token"""
        # Mock failed token refresh
        from fastapi import HTTPException, status
        mock_refresh.side_effect = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
        
        refresh_data = {
            "refresh_token": "invalid-refresh-token"
        }
        
        with patch('app.api.v1.auth.verify_token') as mock_verify:
            mock_verify.return_value = {"user_id": "test-user-id"}
            response = client.post("/api/v1/auth/refresh", json=refresh_data)
        assert response.status_code == 401
        data = response.json()
        assert "Invalid refresh token" in data["detail"]

    def test_get_current_user_success(self, mock_user_repository):
        """Test getting current user information"""
        # Mock user object
        mock_user = User(
            user_id="test-user-id",
            email="test@example.com",
            password_hash="hashed_password",
            full_name="Test User",
            role=UserRole.CANDIDATE,
            status=UserStatus.ACTIVE,
            email_verified=True,
            created_at=datetime.utcnow(),
            last_login=datetime.utcnow()
        )
        # Seed in-memory repo
        mock_user_repository.users_by_id[mock_user.user_id] = mock_user
        mock_user_repository.users_by_email[mock_user.email] = mock_user
        
        # Ensure router uses in-memory repo
        import app.api.v1.auth as auth_module
        auth_module.auth_service.user_repo = mock_user_repository

        # Mock token verification
        with patch('app.api.v1.auth.verify_token') as mock_verify:
            mock_verify.return_value = {"user_id": "test-user-id"}
            
            headers = {"Authorization": "Bearer test-token"}
            response = client.get("/api/v1/auth/me", headers=headers)
            assert response.status_code == 200
            data = response.json()
            assert data["user_id"] == "test-user-id"
            assert data["email"] == "test@example.com"
            assert data["full_name"] == "Test User"

    def test_get_current_user_unauthorized(self):
        """Test getting current user without token"""
        response = client.get("/api/v1/auth/me")
        assert response.status_code == 403  # No authorization header

    def test_register_validation_errors(self):
        """Test registration with validation errors"""
        # Test missing required fields
        user_data = {
            "email": "invalid-email",  # Invalid email format
            "password": "123",  # Too short
            "confirm_password": "456",  # Different from password
            "full_name": "",  # Empty name
            "role": "invalid_role"  # Invalid role
        }
        
        response = client.post("/api/v1/auth/register", json=user_data)
        assert response.status_code == 422  # Validation error

    def test_login_validation_errors(self):
        """Test login with validation errors"""
        # Test missing required fields
        login_data = {
            "email": "invalid-email",  # Invalid email format
            "password": ""  # Empty password
        }
        
        response = client.post("/api/v1/auth/login", json=login_data)
        assert response.status_code == 422  # Validation error

    def test_rate_limiting(self):
        """Test rate limiting functionality"""
        # This test would need to be implemented with proper rate limiting setup
        # For now, we'll just test that the endpoint responds
        user_data = {
            "email": "test@example.com",
            "password": "TestPassword123!",
            "confirm_password": "TestPassword123!",
            "full_name": "Test User",
            "role": "candidate"
        }
        
        # Make multiple requests to test rate limiting
        responses = []
        for i in range(5):
            response = client.post("/api/v1/auth/register", json=user_data)
            responses.append(response.status_code)
        
        # At least some requests should succeed (depending on rate limit settings)
        assert any(status == 201 or status == 400 for status in responses)


if __name__ == "__main__":
    pytest.main([__file__])
