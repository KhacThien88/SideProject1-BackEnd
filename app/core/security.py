from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.core.config import settings
import secrets
import string
import time
import uuid

try:
    import redis
except Exception:  # pragma: no cover
    redis = None

# Security scheme
security = HTTPBearer()


# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


_JWT_PRIVATE_KEY: Optional[str] = None
_JWT_PUBLIC_KEY: Optional[str] = None


def _load_jwt_keys_if_needed() -> None:
    """Load RSA keys from files if configured and algorithm is RS256."""
    global _JWT_PRIVATE_KEY, _JWT_PUBLIC_KEY
    if settings.algorithm.upper() != "RS256":
        return
    if _JWT_PRIVATE_KEY is None and settings.jwt_private_key_path:
        with open(settings.jwt_private_key_path, "r", encoding="utf-8") as f:
            _JWT_PRIVATE_KEY = f.read()
    if _JWT_PUBLIC_KEY is None and settings.jwt_public_key_path:
        with open(settings.jwt_public_key_path, "r", encoding="utf-8") as f:
            _JWT_PUBLIC_KEY = f.read()


def _get_signing_key() -> str:
    if settings.algorithm.upper() == "RS256":
        _load_jwt_keys_if_needed()
        if not _JWT_PRIVATE_KEY:
            raise RuntimeError("RS256 selected but jwt_private_key_path not configured")
        return _JWT_PRIVATE_KEY
    return settings.secret_key


def _get_verification_key() -> str:
    if settings.algorithm.upper() == "RS256":
        _load_jwt_keys_if_needed()
        if not _JWT_PUBLIC_KEY:
            raise RuntimeError("RS256 selected but jwt_public_key_path not configured")
        return _JWT_PUBLIC_KEY
    return settings.secret_key


_redis_client = None


def _get_redis():
    global _redis_client
    if _redis_client is not None:
        return _redis_client
    if redis and settings.redis_url:
        try:
            _redis_client = redis.from_url(settings.redis_url, decode_responses=True)
        except Exception:
            _redis_client = None
    return _redis_client


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash with basic timing measurement."""
    start = time.perf_counter()
    try:
        return pwd_context.verify(plain_password, hashed_password)
    finally:
        duration_ms = (time.perf_counter() - start) * 1000
        # Simple performance monitoring threshold
        if duration_ms > 150:  # configurable in future if needed
            # In production, use proper logging/metrics
            pass


def get_password_hash(password: str) -> str:
    """Hash a password with basic timing measurement."""
    start = time.perf_counter()
    try:
        return pwd_context.hash(password)
    finally:
        _ = (time.perf_counter() - start) * 1000


def needs_hash_upgrade(hashed_password: str) -> bool:
    """Return True if the hash should be upgraded (e.g., higher rounds)."""
    try:
        return pwd_context.needs_update(hashed_password)
    except Exception:
        return False


def _new_jti() -> str:
    return str(uuid.uuid4())


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token with jti and iat."""
    to_encode = data.copy()
    now = datetime.utcnow()
    expire = now + (expires_delta or timedelta(minutes=settings.access_token_expire_minutes))
    to_encode.update({
        "exp": expire,
        "iat": now,
        "type": "access",
        "jti": _new_jti(),
    })
    encoded_jwt = jwt.encode(to_encode, _get_signing_key(), algorithm=settings.algorithm)
    return encoded_jwt


def create_refresh_token(data: Dict[str, Any]) -> str:
    """Create JWT refresh token with jti and iat."""
    to_encode = data.copy()
    now = datetime.utcnow()
    expire = now + timedelta(days=settings.refresh_token_expire_days)
    to_encode.update({
        "exp": expire,
        "iat": now,
        "type": "refresh",
        "jti": _new_jti(),
    })
    encoded_jwt = jwt.encode(to_encode, _get_signing_key(), algorithm=settings.algorithm)
    return encoded_jwt


def _is_blacklisted(jti: Optional[str]) -> bool:
    if not jti:
        return False
    client = _get_redis()
    if not client:
        return False
    try:
        return client.sismember("jwt:blacklist", jti)
    except Exception:
        return False


def _blacklist_jti(jti: Optional[str]) -> None:
    client = _get_redis()
    if not client or not jti:
        return
    try:
        client.sadd("jwt:blacklist", jti)
    except Exception:
        pass


def verify_token(token: str, token_type: str = "access") -> Dict[str, Any]:
    """Verify and decode JWT token; enforce type and blacklist."""
    try:
        payload = jwt.decode(token, _get_verification_key(), algorithms=[settings.algorithm])
        if payload.get("type") != token_type:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type"
            )
        if _is_blacklisted(payload.get("jti")):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has been revoked"
            )
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials"
        )


def generate_verification_token() -> str:
    """Generate email verification token"""
    return ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(32))


def generate_password_reset_token() -> str:
    """Generate secure password reset token."""
    return ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(48))


def validate_password_strength(password: str) -> tuple[bool, str]:
    """Validate password strength"""
    if len(password) < settings.password_min_length:
        return False, f"Password must be at least {settings.password_min_length} characters long"
    
    if settings.password_require_uppercase and not any(c.isupper() for c in password):
        return False, "Password must contain at least one uppercase letter"
    
    if settings.password_require_lowercase and not any(c.islower() for c in password):
        return False, "Password must contain at least one lowercase letter"
    
    if settings.password_require_numbers and not any(c.isdigit() for c in password):
        return False, "Password must contain at least one number"
    
    if settings.password_require_special_chars and not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
        return False, "Password must contain at least one special character"
    
    return True, "Password is valid"


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    """Get current authenticated user from JWT token"""
    try:
        token = credentials.credentials
        payload = verify_token(token, "access")
        user_id = payload.get("user_id")
        
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        
        return {
            "user_id": user_id,
            "email": payload.get("email"),
            "role": payload.get("role")
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials"
        )


def get_admin_user(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """Get current authenticated admin user"""
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user