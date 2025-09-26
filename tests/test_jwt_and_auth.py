import types
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

import pytest

from app.core import security
from app.services.auth_service import AuthService
from app.models.user import User, UserRole, UserStatus, UserSession
from app.core.config import settings


class FakeRedis:
    def __init__(self):
        self._set = set()

    def sadd(self, key, value):
        if key != "jwt:blacklist":
            return 0
        self._set.add(value)
        return 1

    def sismember(self, key, value):
        if key != "jwt:blacklist":
            return False
        return value in self._set


@pytest.fixture
def fake_redis(monkeypatch):
    client = FakeRedis()
    monkeypatch.setattr(security, "_redis_client", client)
    def _get():
        return client
    monkeypatch.setattr(security, "_get_redis", _get)
    return client


def test_jwt_create_and_verify(fake_redis):
    payload = {"user_id": "u1", "email": "a@b.com"}
    token = security.create_access_token(payload, expires_delta=timedelta(minutes=1))
    decoded = security.verify_token(token, "access")
    assert decoded.get("user_id") == "u1"
    assert decoded["type"] == "access"


def test_blacklist_blocks_token(fake_redis):
    payload = {"user_id": "u2"}
    token = security.create_access_token(payload, expires_delta=timedelta(minutes=1))
    decoded = security.verify_token(token, "access")
    jti = decoded.get("jti")
    # put into blacklist
    fake_redis.sadd("jwt:blacklist", jti)
    with pytest.raises(Exception):
        security.verify_token(token, "access")


@pytest.mark.asyncio
async def test_refresh_rotation(monkeypatch):
    svc = AuthService()

    # mock user
    user = User(
        user_id="u3",
        email="u3@example.com",
        password_hash="hash",
        full_name="U3",
        role=UserRole.CANDIDATE,
        status=UserStatus.ACTIVE,
        email_verified=True,
    )

    # create original refresh token
    original_refresh = security.create_refresh_token({"user_id": user.user_id, "email": user.email, "sub": user.user_id})

    # mock repo
    svc.user_repo = MagicMock()
    svc.user_repo.get_user_by_id.return_value = user
    svc.user_repo.get_user_sessions.return_value = [
        UserSession(user_id=user.user_id, access_token="a", refresh_token=original_refresh, expires_at=datetime.utcnow() + timedelta(days=1))
    ]
    svc.user_repo.deactivate_session.return_value = True
    svc.user_repo.create_session.return_value = True

    # act
    resp = await svc.refresh_access_token(original_refresh)

    # assert rotation happened (new refresh != old)
    assert resp.refresh_token != original_refresh
    assert isinstance(resp.access_token, str)
    svc.user_repo.deactivate_session.assert_called()
    svc.user_repo.create_session.assert_called()


