from unittest.mock import MagicMock
import pytest

from app.services.auth_service import AuthService
from app.models.user import User, UserRole, UserStatus
from app.core import security


@pytest.mark.asyncio
async def test_generate_and_reset_password(monkeypatch):
    svc = AuthService()

    user = User(
        user_id="u4",
        email="u4@example.com",
        password_hash="hash",
        full_name="U4",
        role=UserRole.CANDIDATE,
        status=UserStatus.ACTIVE,
        email_verified=True,
    )

    # mock repo
    svc.user_repo = MagicMock()
    svc.user_repo.get_user_by_email.return_value = user
    svc.user_repo.update_user.return_value = True

    ok, token = await svc.generate_password_reset(user.email)
    assert ok is True
    assert isinstance(token, str) and len(token) > 0

    # simulate scan to find token
    from app.core import database
    def fake_scan(table_name):
        return [{"user_id": user.user_id, "reset_token": token, "reset_token_expiry": "2999-01-01T00:00:00"}]
    monkeypatch.setattr(database.db_client, "scan", fake_scan)

    ok2, msg = await svc.reset_password(token, "NewPass123!")
    assert ok2 is True
    assert "reset" in msg.lower()


@pytest.mark.asyncio
async def test_hash_upgrade_on_login(monkeypatch):
    svc = AuthService()

    # create user with old/weak hash so that needs_update returns True
    old_hash = security.get_password_hash("OldPass123!")

    user = User(
        user_id="u6",
        email="u6@example.com",
        password_hash=old_hash,
        full_name="U6",
        role=UserRole.CANDIDATE,
        status=UserStatus.ACTIVE,
        email_verified=True,
    )

    # patch needs_hash_upgrade to force upgrade
    monkeypatch.setattr(security, "needs_hash_upgrade", lambda _h: True)

    svc.user_repo = MagicMock()
    svc.user_repo.get_user_by_email.return_value = user
    svc.user_repo.update_user.return_value = True

    ok_user, msg = await svc.authenticate_user(type("L", (), {"email": user.email, "password": "OldPass123!"})())
    assert ok_user is not None
    svc.user_repo.update_user.assert_called()


