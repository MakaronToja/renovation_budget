"""
Makefile for Renovation Cost Tracker project automation.

Provides convenient commands for development workflow.
"""

.PHONY: help install test test-unit test-integration test-e2e test-coverage lint format security run clean docker-build docker-run

help:  ## Show this help message
	@echo "Renovation Cost Tracker - Available Commands:"
	@echo "=============================================="
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

install:  ## Install dependencies
	pip install -r requirements.txt
	pip install -r requirements-dev.txt

test:  ## Run all tests
	pytest tests/ -v --cov=renovation_cost_tracker --cov-report=html --cov-report=term

test-unit:  ## Run unit tests only
	pytest tests/unit/ -v

test-integration:  ## Run integration tests only
	pytest tests/integration/ -v

test-e2e:  ## Run end-to-end tests
	playwright install
	pytest tests/e2e/ -v

test-coverage:  ## Generate coverage report
	pytest tests/ --cov=renovation_cost_tracker --cov-report=html
	@echo "Coverage report generated in htmlcov/index.html"

lint:  ## Run code linting
	flake8 renovation_cost_tracker/
	mypy renovation_cost_tracker/

format:  ## Format code
	black renovation_cost_tracker/ tests/
	isort renovation_cost_tracker/ tests/

security:  ## Run security checks
	bandit -r renovation_cost_tracker/
	safety check

run:  ## Run development server
	uvicorn renovation_cost_tracker.main:app --reload --host 0.0.0.0 --port 8000

clean:  ## Clean up generated files
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .coverage htmlcov/ .pytest_cache/

docker-build:  ## Build Docker image
	docker build -t renovation-cost-tracker .

docker-run:  ## Run with Docker Compose
	docker-compose up --build

migrate:  ## Run database migrations (if using Alembic)
	alembic upgrade head

migrate-create:  ## Create new migration
	alembic revision --autogenerate -m "$(name)"