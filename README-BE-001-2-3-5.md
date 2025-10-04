BE-001/002/003/005 - Authentication, JWT, Password, User Models

Trạng thái (Done)
- BE-001: Auth APIs (register, login, logout, refresh, me, update me)
- BE-002: JWT (HS256/RS256, jti/iat, verify + blacklist, refresh rotation)
- BE-003: Password (bcrypt, policy/strength, hash upgrade, password reset)
- BE-005: User Models (Pydantic + PynamoDB, GSI: email-index, user-id-index)

Cách chạy nhanh
- Server (dev):
```bash
uvicorn app.main:app --reload
```
- Test (local, không cần AWS):
```bash
python -m pytest -q
```
- Ghi chú test: đang dùng mock (in-memory repo, fake Redis). Chi tiết: .doc-plans/testing-mock-strategy.md

Endpoints chính
- POST /api/v1/auth/register
- POST /api/v1/auth/login
- POST /api/v1/auth/logout
- POST /api/v1/auth/refresh
- GET  /api/v1/auth/me
- PUT  /api/v1/auth/me

Cấu hình tối thiểu (.env)
```env
SECRET_KEY=dev-secret
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
DYNAMODB_REGION=us-east-1
# DYNAMODB_ENDPOINT_URL=http://localhost:8000
REDIS_URL=redis://localhost:6379/0
```

Khi deploy thật
- RS256: đặt ALGORITHM=RS256, cung cấp JWT_PRIVATE_KEY_PATH, JWT_PUBLIC_KEY_PATH
- Bật Redis cho blacklist; tạo DynamoDB tables và GSI (scripts/setup_db.py)

