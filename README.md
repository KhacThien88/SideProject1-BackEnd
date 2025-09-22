# AI Resume Analyzer & Job Match API

Hệ thống API cho phân tích CV và khớp việc làm sử dụng AI, được xây dựng với FastAPI và AWS services.

## Tính năng chính

- **Authentication**: Đăng ký, đăng nhập, quản lý session với JWT
- **CV Upload & Analysis**: Upload và phân tích CV bằng AI
- **Job Matching**: Khớp việc làm thông minh dựa trên CV
- **Real-time Notifications**: Thông báo qua email và chatbot
- **Admin Panel**: Quản lý hệ thống và users

## Cấu trúc dự án

```
app/
├── api/v1/           # API endpoints
│   ├── auth.py       # Authentication endpoints
│   ├── jobs.py       # Job management endpoints
│   └── upload.py     # File upload endpoints
├── core/             # Core configuration
│   ├── config.py     # Application settings
│   ├── database.py   # Database client
│   └── security.py   # Security utilities
├── models/           # Data models
├── repositories/     # Data access layer
├── services/         # Business logic
├── schemas/          # Pydantic schemas
└── middleware/       # Custom middleware
```

## Cài đặt

### 1. Clone repository
```bash
git clone <repository-url>
cd SideProject1-BackEnd
```

### 2. Tạo virtual environment
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# hoặc
venv\Scripts\activate  # Windows
```

### 3. Cài đặt dependencies
```bash
pip install -r requirements.txt
```

### 4. Cấu hình environment variables
Tạo file `.env` từ `.env.example`:
```bash
cp .env.example .env
```

Cập nhật các giá trị trong `.env`:
```env
SECRET_KEY=your-super-secret-key
DYNAMODB_REGION=us-east-1
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
```

### 5. Chạy ứng dụng
```bash
# Development mode
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Production mode
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## API Documentation

Sau khi chạy ứng dụng, truy cập:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health

## Task Documentation

- **BE-001: User Authentication APIs** - [README-BE-001.md](README-BE-001.md)
- **BE-002: JWT Implementation** - (Coming soon)
- **BE-003: Password Hashing** - (Coming soon)
- **BE-004: Email Verification** - (Coming soon)
- **BE-005: User Schema & Models** - (Coming soon)

## Testing

### Chạy tests
```bash
# Chạy tất cả tests
make test

# Chạy tests với coverage
make test-cov

# Test authentication APIs
make test-auth
```

## Database Setup

### DynamoDB Tables

Cần tạo các tables sau trong DynamoDB. Chi tiết setup cho từng task:

- **BE-001 Authentication Tables** - Xem [README-BE-001.md](README-BE-001.md#database-setup)
- **BE-002 JWT Tables** - (Coming soon)
- **BE-003 Password Tables** - (Coming soon)
- **BE-004 Email Tables** - (Coming soon)
- **BE-005 User Schema Tables** - (Coming soon)

## Security Features

- **Authentication**: JWT-based authentication system
- **Authorization**: Role-based access control
- **Rate Limiting**: Request rate limiting per IP
- **Input Validation**: Pydantic schemas với validation rules
- **CORS Protection**: Cấu hình CORS cho production
- **Request Logging**: Log tất cả requests và responses

Chi tiết security features cho từng task:
- **BE-001 Authentication Security** - Xem [README-BE-001.md](README-BE-001.md#security-features)
- **BE-002 JWT Security** - (Coming soon)
- **BE-003 Password Security** - (Coming soon)

## Monitoring & Logging

- **Health Check**: `/health` endpoint
- **Request Logging**: Tự động log tất cả API calls
- **Security Logging**: Log authentication events
- **Error Handling**: Global exception handler

## Development

### Code Style
- Sử dụng Black cho code formatting
- Sử dụng isort cho import sorting
- Sử dụng flake8 cho linting

```bash
# Format code
black app/

# Sort imports
isort app/

# Lint code
flake8 app/
```

### Pre-commit Hooks
```bash
# Cài đặt pre-commit
pip install pre-commit

# Setup hooks
pre-commit install

# Chạy hooks manually
pre-commit run --all-files
```

## Deployment

### Docker
```bash
# Build image
docker build -t ai-resume-api .

# Run container
docker run -p 8000:8000 ai-resume-api
```

### AWS Deployment
- Sử dụng ECS/EKS cho container deployment
- ALB cho load balancing
- CloudWatch cho monitoring
- DynamoDB cho database

## Troubleshooting

### Common Issues

1. **Database Connection Error**
   - Kiểm tra AWS credentials
   - Kiểm tra DynamoDB region
   - Kiểm tra table permissions

2. **JWT Token Error**
   - Kiểm tra SECRET_KEY trong .env
   - Kiểm tra token expiration
   - Kiểm tra token format

3. **Rate Limiting**
   - Kiểm tra rate limit settings
   - Clear rate limit cache nếu cần

### Logs
```bash
# Xem logs
tail -f logs/app.log

# Debug mode
DEBUG=true python -m uvicorn app.main:app --reload
```

## Contributing

1. Fork repository
2. Tạo feature branch
3. Commit changes
4. Push to branch
5. Tạo Pull Request

## License

MIT License - xem file LICENSE để biết thêm chi tiết.