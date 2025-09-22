# 🤖 AI Resume Analyzer & Job Match - Backend

<div align="center">

![Python](https://img.shields.io/badge/Python-3.9+-blue?style=for-the-badge&logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![AWS](https://img.shields.io/badge/AWS-232F3E?style=for-the-badge&logo=amazon-aws&logoColor=white)
![DynamoDB](https://img.shields.io/badge/DynamoDB-4053D6?style=for-the-badge&logo=amazon-dynamodb&logoColor=white)

**🚀 FastAPI backend cho hệ thống AI Resume Analyzer & Job Match**

*Tích hợp DynamoDB, S3, Textract, OpenSearch và SageMaker*

[![API Docs](https://img.shields.io/badge/API-Documentation-green?style=for-the-badge)](http://localhost:8000/docs)
[![Tests](https://img.shields.io/badge/Tests-Passing-brightgreen?style=for-the-badge)]()

</div>

---

## 🚀 Quick Start

```bash
# Clone và setup
git clone <repository-url>
cd backend

# Tạo virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# hoặc
venv\Scripts\activate     # Windows

# Cài đặt dependencies
pip install -r requirements.txt

# Cấu hình environment
cp .env.template .env
# Chỉnh sửa .env với các giá trị thực tế

# Chạy ứng dụng
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## 📚 API Documentation

<div align="center">

| 🔗 Link | 📝 Mô tả |
|---------|----------|
| [Swagger UI](http://localhost:8000/docs) |  Interactive API documentation |
| [ReDoc](http://localhost:8000/redoc) |  Clean API reference |

</div>

## 🏗️ Project Structure

```
app/
├── api/v1/          # API endpoints
├── core/            # Configuration
├── models/          # Database models
├── schemas/         # Pydantic schemas
├── services/        # Business logic
├── repositories/    # Data access
├── utils/           # Utilities
└── middleware/      # Middleware
```

## ✨ Core Features

<div align="center">

| 🎯 Feature | 📝 Description |
|------------|----------------|
| 🔐 **Authentication** | JWT, OAuth, Role-based access |
| 📄 **CV Analysis** | Upload, Textract, AI analysis |
| 🎯 **Job Matching** | AI-powered matching với OpenSearch |
| 📝 **Applications** | Job application workflow |
| 📢 **Notifications** | Email, Slack, WhatsApp |
| 👨‍💼 **Admin Panel** | User/job management, monitoring |

</div>

## 🧪 Testing

```bash
# 🧪 Tất cả tests
pytest

# 📊 Với coverage
pytest --cov=app

# 🎯 Test cụ thể
pytest tests/test_auth.py
```

## 🛠️ Tech Stack

<div align="center">

### 🚀 Backend Framework
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.9+-blue?style=flat-square&logo=python)

### 🗄️ Database & Storage
![DynamoDB](https://img.shields.io/badge/DynamoDB-4053D6?style=flat-square&logo=amazon-dynamodb&logoColor=white)
![S3](https://img.shields.io/badge/S3-569A31?style=flat-square&logo=amazon-s3&logoColor=white)
![OpenSearch](https://img.shields.io/badge/OpenSearch-005571?style=flat-square&logo=opensearch&logoColor=white)

### ☁️ AWS Services
![Textract](https://img.shields.io/badge/Textract-FF9900?style=flat-square&logo=amazon-aws&logoColor=white)
![SageMaker](https://img.shields.io/badge/SageMaker-FF9900?style=flat-square&logo=amazon-aws&logoColor=white)
![SES](https://img.shields.io/badge/SES-FF9900?style=flat-square&logo=amazon-aws&logoColor=white)

### 🤖 AI/ML Libraries
![spaCy](https://img.shields.io/badge/spaCy-09A3D5?style=flat-square&logo=spacy&logoColor=white)
![Transformers](https://img.shields.io/badge/Transformers-FF6B6B?style=flat-square&logo=huggingface&logoColor=white)
![scikit-learn](https://img.shields.io/badge/scikit--learn-F7931E?style=flat-square&logo=scikit-learn&logoColor=white)

</div>

---

<div align="center">

[![GitHub](https://img.shields.io/badge/GitHub-100000?style=for-the-badge&logo=github&logoColor=white)](https://github.com)
[![LinkedIn](https://img.shields.io/badge/LinkedIn-0077B5?style=for-the-badge&logo=linkedin&logoColor=white)](https://linkedin.com)

</div>