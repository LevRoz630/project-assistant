# Build frontend
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Build backend
FROM python:3.11 AS backend-builder
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1
WORKDIR /app
RUN python -m venv .venv
COPY pyproject.toml ./
COPY backend/ ./backend/
RUN .venv/bin/pip install .

# Final stage
FROM python:3.11-slim
WORKDIR /app
COPY --from=backend-builder /app/.venv .venv/
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist
COPY backend/ ./backend/

EXPOSE 8000
CMD ["/bin/sh", "-c", "/app/.venv/bin/uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
