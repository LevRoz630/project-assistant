# Build frontend
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
# Force rebuild: 2026-01-24
RUN npm run build

# Build backend
FROM python:3.11-slim AS backend-builder
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /app

# Install build dependencies for compiling packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Create venv and upgrade pip
RUN python -m venv .venv && \
    .venv/bin/pip install --upgrade pip wheel

# Copy pyproject.toml and create minimal package structure
COPY pyproject.toml ./
RUN mkdir -p backend && echo '__version__ = "0.1.0"' > backend/__init__.py

# Install CPU-only PyTorch first (much smaller than CUDA version)
RUN .venv/bin/pip install torch --index-url https://download.pytorch.org/whl/cpu

# Install package with dependencies (cached unless pyproject.toml changes)
RUN .venv/bin/pip install .

# Clean up to reduce image size
RUN find .venv -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true && \
    find .venv -type d -name "tests" -exec rm -rf {} + 2>/dev/null || true && \
    find .venv -type d -name "test" -exec rm -rf {} + 2>/dev/null || true && \
    find .venv -name "*.pyc" -delete 2>/dev/null || true

# Copy actual backend code (overwrites stub)
COPY backend/ ./backend/

# Final stage
FROM python:3.11-slim
WORKDIR /app

# Copy venv and clean up
COPY --from=backend-builder /app/.venv .venv/
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist
COPY backend/ ./backend/

# Remove any remaining cache files
RUN find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

EXPOSE 8000
CMD ["/bin/sh", "-c", "/app/.venv/bin/uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000} --timeout-keep-alive 120"]
