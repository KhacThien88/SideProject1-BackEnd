# BE-001: User Authentication APIs - Hướng dẫn sử dụng

## Tổng quan

Task BE-001 implement hệ thống authentication hoàn chỉnh với các API endpoints cho đăng ký, đăng nhập, quản lý session và bảo mật.

## Tính năng chính

- ✅ **User Registration** - Đăng ký tài khoản mới với validation
- ✅ **User Login** - Đăng nhập với JWT tokens
- ✅ **Session Management** - Quản lý session và token refresh
- ✅ **User Profile** - Xem và cập nhật thông tin user
- ✅ **Security Features** - Rate limiting, password hashing, logging
- ✅ **Token Management** - Access token và refresh token

## API Endpoints

### Tổng quan Endpoints

| Method | Endpoint | Description | Auth Required | Status Code |
|--------|----------|-------------|---------------|-------------|
| POST | `/api/v1/auth/register` | Đăng ký user mới | ❌ | 201 |
| POST | `/api/v1/auth/login` | Đăng nhập | ❌ | 200 |
| POST | `/api/v1/auth/logout` | Đăng xuất | ✅ | 200 |
| POST | `/api/v1/auth/refresh` | Refresh token | ❌ | 200 |
| GET | `/api/v1/auth/me` | Lấy thông tin user | ✅ | 200 |
| PUT | `/api/v1/auth/me` | Cập nhật user | ✅ | 200 |
| POST | `/api/v1/auth/verify-email` | Xác thực email | ❌ | 200 |

### 1. Đăng ký User mới
```http
POST /api/v1/auth/register
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "SecurePassword123!",
  "confirm_password": "SecurePassword123!",
  "full_name": "John Doe",
  "phone": "+1234567890",
  "role": "candidate"
}
```

**Response:**
```json
{
  "message": "User registered successfully",
  "email": "user@example.com",
  "status": "pending_verification"
}
```

### 2. Đăng nhập
```http
POST /api/v1/auth/login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "SecurePassword123!"
}
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

### 3. Lấy thông tin User hiện tại
```http
GET /api/v1/auth/me
Authorization: Bearer <access_token>
```

**Response:**
```json
{
  "user_id": "user-123",
  "email": "user@example.com",
  "full_name": "John Doe",
  "phone": "+1234567890",
  "role": "candidate",
  "status": "active",
  "email_verified": true,
  "created_at": "2024-01-01T00:00:00Z",
  "last_login": "2024-01-01T12:00:00Z"
}
```

### 4. Cập nhật thông tin User
```http
PUT /api/v1/auth/me
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "full_name": "John Updated",
  "phone": "+0987654321"
}
```

### 5. Refresh Token
```http
POST /api/v1/auth/refresh
Content-Type: application/json

{
  "refresh_token": "<refresh_token>"
}
```

### 6. Đăng xuất
```http
POST /api/v1/auth/logout
Authorization: Bearer <access_token>
```

**Response:**
```json
{
  "message": "Logged out successfully"
}
```

### 7. Xác thực Email
```http
POST /api/v1/auth/verify-email
Content-Type: application/json

{
  "token": "<verification_token>"
}
```

**Response:**
```json
{
  "message": "Email verified successfully"
}
```

## Cài đặt và Chạy

### 1. Cài đặt Dependencies
```bash
# Cài đặt dependencies chính
pip install -r requirements.txt

# Cài đặt dependencies development
pip install -r requirements-dev.txt
```

### 2. Cấu hình Environment
Tạo file `.env`:
```env
# JWT Configuration
SECRET_KEY=your-super-secret-key-change-in-production
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# Database Configuration
DYNAMODB_REGION=us-east-1
DYNAMODB_ENDPOINT_URL=http://localhost:8000  # For local development

# AWS Configuration
AWS_ACCESS_KEY_ID=your-aws-access-key
AWS_SECRET_ACCESS_KEY=your-aws-secret-key
AWS_REGION=us-east-1

# Security Configuration
PASSWORD_MIN_LENGTH=8
PASSWORD_REQUIRE_UPPERCASE=true
PASSWORD_REQUIRE_LOWERCASE=true
PASSWORD_REQUIRE_NUMBERS=true
PASSWORD_REQUIRE_SPECIAL_CHARS=true

# Rate Limiting
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW=60
```

### 3. Chạy Development Server
```bash
# Sử dụng Makefile
make dev

# Hoặc chạy trực tiếp
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 4. Kiểm tra Health
```bash
curl http://localhost:8000/health
```

## Testing

### 1. Chạy Unit Tests
```bash
# Chạy tất cả tests
make test

# Chạy tests với coverage
make test-cov

# Chạy tests cụ thể
pytest tests/test_auth.py -v
```

### 2. Test Authentication APIs
```bash
# Test toàn bộ authentication flow
make test-auth

# Test với verbose output
make test-auth-verbose

# Test với custom URL
python scripts/test_auth_api.py --url http://localhost:8000
```

### 3. Manual Testing với cURL

#### Đăng ký User
```bash
curl -X POST "http://localhost:8000/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "TestPassword123!",
    "confirm_password": "TestPassword123!",
    "full_name": "Test User",
    "role": "candidate"
  }'
```

#### Đăng nhập
```bash
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "TestPassword123!"
  }'
```

#### Lấy thông tin User
```bash
curl -X GET "http://localhost:8000/api/v1/auth/me" \
  -H "Authorization: Bearer <access_token>"
```

## API Documentation

Sau khi chạy server, truy cập:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

## Database Setup

### DynamoDB Tables

Cần tạo các tables sau:

#### 1. Users Table
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

#### 2. User Sessions Table
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

## Security Features

### 1. Password Requirements
- Tối thiểu 8 ký tự
- Phải có chữ hoa
- Phải có chữ thường  
- Phải có số
- Phải có ký tự đặc biệt

### 2. JWT Tokens
- **Access Token**: 30 phút
- **Refresh Token**: 7 ngày
- **Algorithm**: HS256
- **Secret Key**: Cấu hình trong environment
- **Token Rotation**: Refresh token được rotate mỗi lần refresh

### 3. Rate Limiting
- **100 requests/phút** per IP
- **Window**: 60 giây
- **Response**: 429 Too Many Requests
- **Bypass**: Health check endpoints

### 4. Request Logging
- Log tất cả authentication events
- Security monitoring
- Error tracking
- IP address tracking
- User agent logging

### 5. Session Management
- **Session Invalidation**: Logout invalidates all sessions
- **Token Blacklisting**: Expired tokens are blacklisted
- **Concurrent Sessions**: Multiple sessions per user supported
- **Session Timeout**: Automatic session cleanup

### 6. Input Validation
- **Email Validation**: RFC 5322 compliant
- **Password Strength**: Configurable requirements
- **SQL Injection Protection**: Parameterized queries
- **XSS Protection**: Input sanitization

## Error Handling

### HTTP Status Codes
- `200` - Success
- `201` - Created (registration)
- `400` - Bad Request (validation errors)
- `401` - Unauthorized (invalid credentials)
- `403` - Forbidden (no token)
- `422` - Validation Error (invalid input)
- `429` - Too Many Requests (rate limit)
- `500` - Internal Server Error

### Error Response Format
```json
{
  "detail": "Error message",
  "timestamp": "2024-01-01T00:00:00Z"
}
```

### Common Error Scenarios

#### Registration Errors
```json
// Email already exists
{
  "detail": "Email already registered"
}

// Password mismatch
{
  "detail": "Passwords do not match"
}

// Weak password
{
  "detail": "Password must be at least 8 characters long"
}
```

#### Login Errors
```json
// Invalid credentials
{
  "detail": "Invalid email or password"
}

// Account not verified
{
  "detail": "Please verify your email before logging in"
}

// Account suspended
{
  "detail": "Your account has been suspended"
}
```

#### Token Errors
```json
// Invalid token
{
  "detail": "Could not validate credentials"
}

// Expired token
{
  "detail": "Token has expired"
}

// Invalid token type
{
  "detail": "Invalid token type"
}
```

## Development Commands

```bash
# Development
make dev              # Chạy development server
make install         # Cài đặt dependencies
make clean           # Clean up temporary files

# Testing
make test            # Chạy unit tests
make test-cov        # Chạy tests với coverage
make test-auth       # Test authentication APIs

# Code Quality
make lint            # Run linting
make format          # Format code

# Docker
make docker-build    # Build Docker image
make docker-up      # Start development environment
make docker-down    # Stop development environment
```

## Troubleshooting

### Common Issues

#### 1. Database Connection Error
```bash
# Kiểm tra AWS credentials
aws sts get-caller-identity

# Kiểm tra DynamoDB region
aws dynamodb list-tables --region us-east-1
```

#### 2. JWT Token Error
```bash
# Kiểm tra SECRET_KEY trong .env
echo $SECRET_KEY

# Kiểm tra token format
echo "your-token" | base64 -d
```

#### 3. Rate Limiting
```bash
# Clear rate limit cache (restart server)
make dev

# Kiểm tra rate limit settings
grep RATE_LIMIT .env
```

### Logs
```bash
# Xem logs trong development
tail -f logs/app.log

# Debug mode
DEBUG=true make dev
```

## Production Deployment

### 1. Environment Variables
```env
DEBUG=false
SECRET_KEY=production-secret-key
DYNAMODB_REGION=us-east-1
RATE_LIMIT_REQUESTS=1000
```

### 2. Docker Deployment
```bash
# Build production image
make prod-build

# Run container
docker run -p 8000:8000 ai-resume-analyzer-backend:latest
```

### 3. Health Check
```bash
# Production health check
curl -f http://localhost:8000/health
```

## API Examples

### Complete Authentication Flow

#### 1. Register User
```bash
curl -X POST "http://localhost:8000/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "newuser@example.com",
    "password": "SecurePassword123!",
    "confirm_password": "SecurePassword123!",
    "full_name": "New User",
    "phone": "+1234567890",
    "role": "candidate"
  }'
```

#### 2. Login
```bash
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "newuser@example.com",
    "password": "SecurePassword123!"
  }'
```

#### 3. Get User Info
```bash
curl -X GET "http://localhost:8000/api/v1/auth/me" \
  -H "Authorization: Bearer <access_token>"
```

#### 4. Update User
```bash
curl -X PUT "http://localhost:8000/api/v1/auth/me" \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "full_name": "Updated Name",
    "phone": "+0987654321"
  }'
```

#### 5. Refresh Token
```bash
curl -X POST "http://localhost:8000/api/v1/auth/refresh" \
  -H "Content-Type: application/json" \
  -d '{
    "refresh_token": "<refresh_token>"
  }'
```

#### 6. Logout
```bash
curl -X POST "http://localhost:8000/api/v1/auth/logout" \
  -H "Authorization: Bearer <access_token>"
```

## Monitoring

### Health Check
```bash
curl http://localhost:8000/health
```

### Metrics
- Request count
- Response time
- Error rate
- Authentication success rate

### Logs
- Authentication events
- Security events
- Error logs
- Performance metrics

## Architecture Overview

### System Components

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   FastAPI       │    │   DynamoDB      │
│   (React)       │◄──►│   Backend       │◄──►│   Database      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │
                              ▼
                       ┌─────────────────┐
                       │   AWS Services  │
                       │   (SES, S3)     │
                       └─────────────────┘
```

### Authentication Flow

```
1. User Registration
   ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
   │   Frontend  │───►│   FastAPI   │───►│  DynamoDB   │
   │             │    │             │    │             │
   └─────────────┘    └─────────────┘    └─────────────┘

2. User Login
   ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
   │   Frontend  │◄───│   FastAPI   │◄───│  DynamoDB   │
   │             │    │             │    │             │
   └─────────────┘    └─────────────┘    └─────────────┘
         │                   │
         ▼                   ▼
   ┌─────────────┐    ┌─────────────┐
   │ JWT Tokens  │    │   Session   │
   │             │    │  Storage    │
   └─────────────┘    └─────────────┘
```

### Data Models

#### User Model
```python
{
  "user_id": "uuid",
  "email": "user@example.com",
  "password_hash": "bcrypt_hash",
  "full_name": "John Doe",
  "phone": "+1234567890",
  "role": "candidate|recruiter|admin",
  "status": "active|inactive|pending_verification|suspended",
  "email_verified": true,
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z",
  "last_login": "2024-01-01T12:00:00Z"
}
```

#### Session Model
```python
{
  "session_id": "uuid",
  "user_id": "uuid",
  "access_token": "jwt_token",
  "refresh_token": "jwt_token",
  "expires_at": "2024-01-08T00:00:00Z",
  "created_at": "2024-01-01T00:00:00Z",
  "is_active": true
}
```

## Performance Considerations

### Database Optimization
- **GSI Indexing**: Email index for fast lookups
- **Batch Operations**: Bulk user operations
- **Connection Pooling**: Reuse database connections
- **Query Optimization**: Efficient DynamoDB queries

### Caching Strategy
- **Token Caching**: Cache valid tokens
- **User Data Caching**: Cache user profiles
- **Rate Limit Caching**: In-memory rate limiting
- **Session Caching**: Active session tracking

### Scalability
- **Horizontal Scaling**: Multiple FastAPI instances
- **Load Balancing**: ALB distribution
- **Auto Scaling**: Dynamic instance scaling
- **Database Scaling**: DynamoDB auto-scaling

## Task Dependencies

### BE-001 đã bao gồm:
- ✅ **BE-002: JWT Implementation** - Đã implement trong `app/core/security.py`
- ✅ **BE-003: Password Hashing** - Đã implement trong `app/core/security.py`
- ✅ **BE-005: User Schema & Models** - Đã implement trong `app/models/user.py`

### BE-001 chưa bao gồm:
- ❌ **BE-004: Email Verification** - Chưa implement (optional feature)

### Lý do tích hợp:
- **BE-001 cần JWT** để tạo và validate authentication tokens
- **BE-001 cần Password Hashing** để bảo mật user passwords
- **BE-001 cần User Models** để định nghĩa data structure
- **BE-004 là optional** - Authentication có thể hoạt động mà không cần email verification

## Next Steps

Sau khi hoàn thành BE-001 (bao gồm BE-002, BE-003, BE-005), có thể tiếp tục với:
- **BE-004**: Email Verification (AWS SES integration) - **Optional feature**
- **BE-006**: File Upload API (CV upload functionality)
- **BE-007**: S3 Integration (File storage)
- **BE-008**: Textract Integration (CV text extraction)

### Priority Order:
1. **BE-004** (Email Verification) - Có thể implement sau để hoàn thiện authentication
2. **BE-006** (File Upload) - Bắt đầu CV upload functionality
3. **BE-007** (S3 Integration) - File storage cho CV files
4. **BE-008** (Textract) - AI text extraction từ CV

## FAQ (Frequently Asked Questions)

### Q: Làm sao để test authentication APIs?
A: Sử dụng `make test-auth` hoặc chạy `python scripts/test_auth_api.py`

### Q: Token hết hạn thì làm sao?
A: Sử dụng refresh token để lấy access token mới qua endpoint `/api/v1/auth/refresh`

### Q: Có thể đăng nhập từ nhiều thiết bị không?
A: Có, hệ thống hỗ trợ multiple sessions per user

### Q: Làm sao để đăng xuất tất cả thiết bị?
A: Gọi endpoint `/api/v1/auth/logout` sẽ invalidate tất cả sessions

### Q: Password requirements là gì?
A: Tối thiểu 8 ký tự, có chữ hoa, chữ thường, số và ký tự đặc biệt

### Q: Rate limit là bao nhiêu?
A: 100 requests/phút per IP address

### Q: Làm sao để debug authentication issues?
A: Kiểm tra logs, health check endpoint, và database connection

### Q: Có thể customize password requirements không?
A: Có, cấu hình trong file `.env` với các biến `PASSWORD_*`

### Q: JWT token có thể decode được không?
A: Có, nhưng cần secret key để verify signature

### Q: Session được lưu ở đâu?
A: Session được lưu trong DynamoDB table `user_sessions`

## Support

Nếu gặp vấn đề, hãy kiểm tra:
1. Logs trong console
2. Health check endpoint
3. Database connection
4. Environment variables
5. API documentation tại `/docs`

### Contact Information
- **Documentation**: README-BE-001.md
- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health
- **Test Script**: `scripts/test_auth_api.py`
