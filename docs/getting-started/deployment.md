# Deployment

This guide covers deploying the Personal AI Assistant using Docker and Fly.io.

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
- **flyctl** - Fly.io CLI
- **gh** - GitHub CLI
- **node/npm** - Node.js 20
- **python3** - Python 3.11
- **git** - Version control

### Production Docker Image

Build a single production image that includes frontend, backend, and nginx:

```bash
# Build
docker build -f Dockerfile.fly -t project-assistant .

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
Dockerfile.fly (Production)
├── Stage 1: Build frontend (node:20-alpine)
│   └── npm ci && npm run build
└── Stage 2: Runtime (python:3.11-slim)
    ├── nginx (serves frontend, proxies /api/ and /auth/)
    └── uvicorn (FastAPI backend on localhost:8000)
```

## Fly.io Deployment

[Fly.io](https://fly.io) provides simple container deployment with persistent volumes.

### Prerequisites

1. Install flyctl: https://fly.io/docs/hands-on/install-flyctl/
2. Create an account: `flyctl auth signup`
3. Authenticate: `flyctl auth login`

### Initial Setup

1. Create the app:

```bash
flyctl apps create project-assistant
```

2. Create a persistent volume for ChromaDB data:

```bash
flyctl volumes create chromadb_data --region lhr --size 1
```

The volume persists across deployments and machine restarts.

3. Set secrets (sensitive environment variables):

```bash
flyctl secrets set \
  AZURE_CLIENT_ID=your-client-id \
  AZURE_CLIENT_SECRET=your-client-secret \
  ANTHROPIC_API_KEY=your-anthropic-key \
  OPENAI_API_KEY=your-openai-key \
  GOOGLE_API_KEY=your-google-key \
  SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))") \
  GITHUB_TOKEN=your-github-token
```

### Configuration (fly.toml)

The `fly.toml` file configures the deployment:

```toml
app = "project-assistant"
primary_region = "lhr"

[build]
  builder = "dockerfile"
  dockerfile = "Dockerfile.fly"

[env]
  DEBUG = "false"
  CHROMA_PERSIST_DIRECTORY = "/app/data/chroma"
  FRONTEND_URL = "https://project-assistant.fly.dev"

[http_service]
  internal_port = 8080
  force_https = true
  auto_stop_machines = "stop"
  auto_start_machines = true

[[vm]]
  memory = "1gb"
  cpu_kind = "shared"
  cpus = 1

[mounts]
  source = "chromadb_data"
  destination = "/app/data"
```

Key settings:
- **primary_region**: Choose a region near you (lhr = London)
- **auto_stop_machines**: Stops VM when idle to save costs
- **memory**: 1GB recommended for LangChain/ChromaDB
- **mounts**: Persists `/app/data` across deployments

### Deploy

```bash
flyctl deploy
```

The app will be available at `https://project-assistant.fly.dev`

### Post-Deployment

1. **Update Azure Redirect URI**

   Add the production callback URL to your Azure AD app:
   - `https://project-assistant.fly.dev/auth/callback`

2. **Check logs**

```bash
flyctl logs
```

3. **Open the app**

```bash
flyctl open
```

4. **Check status**

```bash
flyctl status
```

### Scaling

Adjust resources in `fly.toml`:

```toml
[[vm]]
  memory = "2gb"   # More memory for larger vector stores
  cpu_kind = "shared"
  cpus = 2
```

Then redeploy: `flyctl deploy`

### Custom Domain

1. Add a custom domain:

```bash
flyctl certs create your-domain.com
```

2. Update DNS with the provided CNAME
3. Update `FRONTEND_URL` and Azure redirect URI

### Monitoring

View metrics in the Fly.io dashboard or via CLI:

```bash
flyctl dashboard
flyctl status
flyctl logs --app project-assistant
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
flyctl logs --app project-assistant
docker build -f Dockerfile.fly . 2>&1 | less
```

### Volume Issues

Verify volume is mounted:
```bash
flyctl ssh console
ls -la /app/data
```

### Memory Issues

Increase VM memory in `fly.toml` and redeploy.

### OAuth Callback Errors

Verify redirect URI matches exactly in Azure AD:
- Local: `http://localhost:8000/auth/callback`
- Production: `https://your-app.fly.dev/auth/callback`
