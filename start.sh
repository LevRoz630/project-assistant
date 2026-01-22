#!/bin/bash
set -e

# Create data directory if it doesn't exist
mkdir -p /app/data/chroma

# Start uvicorn backend in background
cd /app/backend
uvicorn main:app --host 127.0.0.1 --port 8000 &

# Wait for backend to be ready
echo "Waiting for backend to start..."
for i in {1..30}; do
    if curl -s http://127.0.0.1:8000/health > /dev/null 2>&1; then
        echo "Backend is ready"
        break
    fi
    sleep 1
done

# Start nginx in foreground
echo "Starting nginx..."
nginx -g "daemon off;"
