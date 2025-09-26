from datetime import datetime


def make_user_payload(email: str = "user@example.com") -> dict:
    return {
        "email": email,
        "password": "TestPassword123!",
        "confirm_password": "TestPassword123!",
        "full_name": "Test User",
        "phone": "+1234567890",
        "role": "candidate",
    }


def make_login_payload(email: str = "user@example.com") -> dict:
    return {
        "email": email,
        "password": "TestPassword123!",
    }


