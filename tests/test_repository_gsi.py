from unittest.mock import MagicMock

from app.repositories.user import UserRepository
from app.models.user import User, UserRole, UserStatus, UserSession


def test_get_user_by_email_gsi(monkeypatch):
    repo = UserRepository()

    class FakeItem:
        def __init__(self):
            self.user_id = "u5"
            self.email = "u5@example.com"
            self.password_hash = "h"
            self.full_name = "U5"
            self.phone = ""
            self.role = "candidate"
            self.status = "active"
            self.email_verified = True
            from datetime import datetime
            self.created_at = datetime.utcnow()
            self.updated_at = self.created_at
            self.last_login = None

    class FakeIndex:
        def query(self, email):
            yield FakeItem()

    class FakeUserTable:
        email_index = FakeIndex()

    # patch model
    import app.models.user as user_models
    monkeypatch.setattr(user_models, "UserTable", FakeUserTable)
    # Patch repository module reference as well
    import app.repositories.user as repo_mod
    monkeypatch.setattr(repo_mod, "UserTable", FakeUserTable)

    user = repo.get_user_by_email("u5@example.com")
    assert user is not None
    assert user.email == "u5@example.com"


def test_get_user_sessions_gsi(monkeypatch):
    repo = UserRepository()

    class FakeItem:
        def __init__(self):
            from datetime import datetime, timedelta
            self.session_id = "s1"
            self.user_id = "u5"
            self.access_token = "a"
            self.refresh_token = "r"
            self.expires_at = datetime.utcnow() + timedelta(days=1)
            self.created_at = datetime.utcnow()
            self.is_active = True

    class FakeIndex:
        def query(self, user_id):
            yield FakeItem()

    class FakeSessionTable:
        user_id_index = FakeIndex()

    import app.models.user as user_models
    monkeypatch.setattr(user_models, "UserSessionTable", FakeSessionTable)
    import app.repositories.user as repo_mod
    monkeypatch.setattr(repo_mod, "UserSessionTable", FakeSessionTable)

    sessions = repo.get_user_sessions("u5")
    assert len(sessions) == 1
    assert sessions[0].user_id == "u5"


