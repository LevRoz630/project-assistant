.PHONY: help install install-dev test test-cov lint format type-check pre-commit clean backend frontend dev

# Default target
help:
	@echo "Personal AI Assistant - Development Commands"
	@echo ""
	@echo "Setup:"
	@echo "  make install       Install production dependencies"
	@echo "  make install-dev   Install development dependencies"
	@echo ""
	@echo "Testing:"
	@echo "  make test          Run tests"
	@echo "  make test-cov      Run tests with coverage"
	@echo "  make test-watch    Run tests in watch mode"
	@echo ""
	@echo "Code Quality:"
	@echo "  make lint          Run linter (ruff)"
	@echo "  make format        Format code (ruff format)"
	@echo "  make type-check    Run type checker (mypy)"
	@echo "  make check         Run all checks (lint + type-check + test)"
	@echo ""
	@echo "Development:"
	@echo "  make backend       Start backend server"
	@echo "  make frontend      Start frontend dev server"
	@echo "  make dev           Start both servers"
	@echo ""
	@echo "Maintenance:"
	@echo "  make clean         Clean build artifacts"
	@echo "  make pre-commit    Install pre-commit hooks"

# Installation
install:
	pip install -r requirements.txt

install-dev:
	pip install -e ".[dev]"
	cd frontend && npm install

# Testing
test:
	cd backend && python -m pytest ../tests -v

test-cov:
	cd backend && python -m pytest ../tests -v --cov=. --cov-report=html --cov-report=term-missing

test-watch:
	cd backend && python -m pytest ../tests -v --watch

# Code Quality
lint:
	ruff check backend tests

lint-fix:
	ruff check backend tests --fix

format:
	ruff format backend tests

format-check:
	ruff format backend tests --check

type-check:
	cd backend && python -m mypy . --ignore-missing-imports

check: lint type-check test

# Development Servers
backend:
	cd backend && uvicorn main:app --reload --host 0.0.0.0 --port 8000

frontend:
	cd frontend && npm run dev

dev:
	@echo "Starting backend and frontend..."
	@make backend & make frontend

# Pre-commit
pre-commit:
	pre-commit install
	pre-commit install --hook-type commit-msg

pre-commit-run:
	pre-commit run --all-files

# Cleanup
clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name htmlcov -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name ".coverage" -delete 2>/dev/null || true

# Docker
docker-build:
	docker-compose build

docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

docker-logs:
	docker-compose logs -f
