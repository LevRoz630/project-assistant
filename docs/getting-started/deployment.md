# Deployment

This guide covers deploying the Personal AI Assistant using Docker and Railway.

## Docker Deployment

### Development with Docker Compose

The simplest way to run both frontend and backend locally:

```bash
docker-compose up --build
```

This starts:
- **Backend**: http://localhost:8000 (FastAPI with hot reload)
- **Frontend**: http://localhost:5173 (Vite with hot reload)

The compose file mounts source directories for live code changes.

### Development Container

A full development environment container is available with pre-installed tools:

```bash
# Build the container
docker build -f Dockerfile.dev -t project-assistant-dev .

# Run interactively with project mounted
docker run -it -v $(pwd):/workspace project-assistant-dev
```

Included tools:
- **claude** - Claude Code CLI
- **gh** - GitHub CLI
- **node/npm** - Node.js 20
- **python3** - Python 3.11
- **git** - Version control

### Production Docker Image

Build a single production image that includes frontend, backend, and nginx:

```bash
# Build
docker build -t project-assistant .

# Run
docker run -p 8080:8080 --env-file .env project-assistant
```

The production image:
- Builds frontend static files
- Runs backend via uvicorn
- Serves frontend via nginx
- Proxies API requests to backend
- Exposes port 8080

### Container Architecture

```
Dockerfile (Production)
├── Stage 1: Build frontend (node:20-alpine)
│   └── npm ci && npm run build
└── Stage 2: Runtime (python:3.11-slim)
    ├── nginx (serves frontend, proxies /api/ and /auth/)
    └── uvicorn (FastAPI backend on localhost:8000)
```

## Production Checklist

Before going to production:

1. Set `DEBUG=false`
2. Generate secure `SECRET_KEY`
3. Update `FRONTEND_URL` to production URL
4. Add production redirect URI in Azure AD
5. Configure rate limiting (consider Redis for distributed)
6. Set up monitoring and alerting
7. Enable backups for volumes
8. Review security settings

## Nginx Configuration

The production image uses nginx to:
- Serve static frontend files
- Proxy `/api/*` to backend
- Proxy `/auth/*` for OAuth callbacks
- Enable gzip compression
- Add cache headers for assets

Config location in container: `/etc/nginx/sites-available/default`

```nginx
server {
    listen 8080;
    root /app/frontend/dist;

    location /api/ {
        proxy_pass http://127.0.0.1:8000/;
    }

    location /auth/ {
        proxy_pass http://127.0.0.1:8000/auth/;
    }

    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

## Troubleshooting

### Build Failures

Check Docker build logs:
```bash
docker build . 2>&1 | less
```

### OAuth Callback Errors

Verify redirect URI matches exactly in Azure AD:
- Local: `http://localhost:8000/auth/callback`
- Production: `https://your-app.up.railway.app/auth/callback`
