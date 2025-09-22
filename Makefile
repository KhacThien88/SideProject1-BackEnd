# AI Resume Analyzer & Job Match - Backend
# Makefile for development and deployment

.PHONY: help install dev test lint format clean docker-build docker-up docker-down

# Default target
help: ## Show this help message
	@echo "AI Resume Analyzer & Job Match - Backend"
	@echo "========================================"
	@echo ""
	@echo "Available commands:"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

# Development setup
install: ## Install dependencies
	pip install -r requirements.txt
	pip install -r requirements-dev.txt

dev: ## Run development server
	uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Testing
test: ## Run tests
	pytest

test-cov: ## Run tests with coverage
	pytest --cov=app --cov-report=html --cov-report=term

# Code quality
lint: ## Run linting
	flake8 app tests
	mypy app

format: ## Format code
	black app tests
	isort app tests

# Docker commands
docker-build: ## Build Docker image
	docker build -t ai-resume-analyzer-backend .

docker-up: ## Start development environment
	docker-compose -f docker-compose.dev.yml up -d

docker-down: ## Stop development environment
	docker-compose -f docker-compose.dev.yml down

docker-logs: ## Show Docker logs
	docker-compose -f docker-compose.dev.yml logs -f

# Database commands
db-setup: ## Setup local database
	python scripts/setup_db.py

db-migrate: ## Run database migrations
	python scripts/migrate_data.py

# AI/ML commands
test-ai: ## Test AI models
	python scripts/test_ai_models.py

# Cleanup
clean: ## Clean up temporary files
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -delete
	rm -rf build/
	rm -rf dist/
	rm -rf .coverage
	rm -rf htmlcov/
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/

# Production commands
prod-build: ## Build production Docker image
	docker build -t ai-resume-analyzer-backend:latest .

prod-deploy: ## Deploy to production
	@echo "Deploying to production..."
	# Add your deployment commands here

# Health check
health: ## Check application health
	curl -f http://localhost:8000/health || echo "Health check failed"

# Documentation
docs: ## Generate documentation
	mkdocs serve

# Security
security: ## Run security checks
	bandit -r app
	safety check

# Performance
perf: ## Run performance tests
	locust -f tests/performance/locustfile.py --host=http://localhost:8000

# Backup
backup: ## Backup database
	@echo "Creating database backup..."
	# Add your backup commands here

# Restore
restore: ## Restore database
	@echo "Restoring database..."
	# Add your restore commands here
