# BE-001: User Authentication APIs

## Tổng quan

Hệ thống authentication hoàn chỉnh với JWT tokens, đăng ký/đăng nhập user, và quản lý session.

## Tính năng chính

- ✅ Đăng ký user mới với validation
- ✅ Đăng nhập với JWT tokens
- ✅ Quản lý session và refresh token
- ✅ Xem/cập nhật thông tin user
- ✅ Rate limiting và security

## API Endpoints

| Method | Endpoint | Mô tả | Auth |
|--------|----------|-------|------|
| POST | `/api/v1/auth/register` | Đăng ký user | ❌ |
| POST | `/api/v1/auth/login` | Đăng nhập | ❌ |
| GET | `/api/v1/auth/me` | Thông tin user | ✅ |
| PUT | `/api/v1/auth/me` | Cập nhật user | ✅ |
| POST | `/api/v1/auth/refresh` | Refresh token | ❌ |
| POST | `/api/v1/auth/logout` | Đăng xuất | ✅ |

## Ví dụ sử dụng

### 1. Đăng ký user
```bash
curl -X POST "http://localhost:8000/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "SecurePass123!",
    "confirm_password": "SecurePass123!",
    "full_name": "John Doe",
    "role": "candidate"
  }'
```

### 2. Đăng nhập
```bash
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "SecurePass123!"
  }'
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

### 3. Lấy thông tin user
```bash
curl -X GET "http://localhost:8000/api/v1/auth/me" \
  -H "Authorization: Bearer <access_token>"
```

### 4. Refresh token
```bash
curl -X POST "http://localhost:8000/api/v1/auth/refresh" \
  -H "Content-Type: application/json" \
  -d '{"refresh_token": "<refresh_token>"}'
```

## Cài đặt và chạy

### 1. Cài đặt dependencies
```bash
pip install -r requirements.txt
```

### 2. Cấu hình .env
```env
# JWT Configuration
SECRET_KEY=your-super-secret-key-change-in-production
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# Database Configuration
DYNAMODB_REGION=us-east-1
DYNAMODB_ENDPOINT_URL=http://localhost:8000

# Security Configuration
PASSWORD_MIN_LENGTH=8
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW=60
```

### 3. Chạy server
```bash
# Development
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Hoặc sử dụng Makefile
make dev
```

### 4. Kiểm tra health
```bash
curl http://localhost:8000/health
```

## Testing

### Chạy tests
```bash
# Tất cả tests
make test

# Test authentication
make test-auth

# Test với coverage
make test-cov
```

### Test manual
```bash
# Test authentication flow
python scripts/test_auth_api.py

# Test với custom URL
python scripts/test_auth_api.py --url http://localhost:8000
```

## API Documentation

Sau khi chạy server:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Security Features

### Password Requirements
- Tối thiểu 8 ký tự
- Có chữ hoa, chữ thường, số và ký tự đặc biệt

### JWT Tokens
- **Access Token**: 30 phút
- **Refresh Token**: 7 ngày
- **Algorithm**: HS256

### Rate Limiting
- **100 requests/phút** per IP
- Response: 429 Too Many Requests

## Error Handling

### HTTP Status Codes
- `200` - Success
- `201` - Created
- `400` - Bad Request
- `401` - Unauthorized
- `422` - Validation Error
- `429` - Too Many Requests
- `500` - Internal Server Error

### Error Response Format
```json
{
  "detail": "Error message",
  "timestamp": "2024-01-01T00:00:00Z"
}
```

## Database Setup

### DynamoDB Tables

#### Users Table
```bash
aws dynamodb create-table \
  --table-name users \
  --attribute-definitions \
    AttributeName=user_id,AttributeType=S \
    AttributeName=email,AttributeType=S \
  --key-schema \
    AttributeName=user_id,KeyType=HASH \
  --global-secondary-indexes \
    IndexName=email-index,KeySchema=[{AttributeName=email,KeyType=HASH}],Projection={ProjectionType=ALL} \
  --billing-mode PAY_PER_REQUEST
```

#### User Sessions Table
```bash
aws dynamodb create-table \
  --table-name user_sessions \
  --attribute-definitions \
    AttributeName=session_id,AttributeType=S \
    AttributeName=user_id,AttributeType=S \
  --key-schema \
    AttributeName=session_id,KeyType=HASH \
  --global-secondary-indexes \
    IndexName=user-id-index,KeySchema=[{AttributeName=user_id,KeyType=HASH}],Projection={ProjectionType=ALL} \
  --billing-mode PAY_PER_REQUEST
```

## Troubleshooting

### Common Issues

1. **Database Connection Error**
   ```bash
   # Kiểm tra AWS credentials
   aws sts get-caller-identity
   ```

2. **JWT Token Error**
   ```bash
   # Kiểm tra SECRET_KEY
   echo $SECRET_KEY
   ```

3. **Rate Limiting**
   ```bash
   # Restart server để clear cache
   make dev
   ```

## FAQ

**Q: Token hết hạn thì làm sao?**
A: Sử dụng refresh token qua endpoint `/api/v1/auth/refresh`

**Q: Password requirements là gì?**
A: Tối thiểu 8 ký tự, có chữ hoa, chữ thường, số và ký tự đặc biệt

**Q: Rate limit là bao nhiêu?**
A: 100 requests/phút per IP address

**Q: Có thể đăng nhập từ nhiều thiết bị không?**
A: Có, hệ thống hỗ trợ multiple sessions per user

## Support

Nếu gặp vấn đề:
1. Kiểm tra logs trong console
2. Health check: http://localhost:8000/health
3. API docs: http://localhost:8000/docs
4. Test script: `scripts/test_auth_api.py`
