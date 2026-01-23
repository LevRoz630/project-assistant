# Installation

## Prerequisites

- **Python 3.11+** - Backend runtime
- **Node.js 18+** - Frontend build tools
- **Git** - Version control

Optional:
- **Docker** - For containerized deployment
- **flyctl** - For Fly.io deployment

## Clone Repository

```bash
git clone https://github.com/your-org/project-assistant.git
cd project-assistant
```

## Option 1: Local Development Setup

### Backend Setup

1. Create a virtual environment:

```bash
cd backend
python -m venv venv

# Activate on Linux/Mac
source venv/bin/activate

# Activate on Windows
venv\Scripts\activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

For development with testing tools:
```bash
pip install -e ".[dev]"
```

3. Create environment file:

```bash
cp .env.example .env
```

4. Edit `.env` with your credentials (see [Configuration](configuration.md))

5. Run the backend:

```bash
uvicorn main:app --reload --port 8000
```

The API will be available at http://localhost:8000

### Frontend Setup

1. Install dependencies:

```bash
cd frontend
npm install
```

2. Run the development server:

```bash
npm run dev
```

The frontend will be available at http://localhost:5173

## Option 2: Docker Compose

The simplest way to run both services:

```bash
# From project root
docker-compose up --build
```

This starts:
- Backend at http://localhost:8000
- Frontend at http://localhost:5173

See [Deployment](deployment.md) for production Docker setup.

## Verify Installation

1. Open http://localhost:5173 in your browser
2. Click "Login with Microsoft"
3. Authorize the application
4. Start chatting with your AI assistant

## Directory Structure

After installation, your project should look like:

```
project-assistant/
├── backend/
│   ├── main.py
│   ├── config.py
│   ├── routers/
│   └── services/
├── frontend/
│   ├── src/
│   └── package.json
├── tests/
├── docs/
├── data/              # Created on first run
│   ├── chroma/        # Vector store
│   └── arxiv/         # ArXiv digests
├── .env               # Your configuration
├── .env.example
├── requirements.txt
├── docker-compose.yml
├── Dockerfile.fly
└── fly.toml
```

## Troubleshooting

### Port Already in Use

```bash
# Find process on port 8000 (Linux/Mac)
lsof -i :8000

# Kill it
kill -9 <PID>
```

On Windows:
```powershell
netstat -ano | findstr :8000
taskkill /PID <PID> /F
```

### Missing Dependencies

```bash
# Reinstall Python dependencies
pip install -r requirements.txt --upgrade

# Reinstall Node dependencies
cd frontend && rm -rf node_modules && npm install
```

### Azure Authentication Fails

1. Verify Azure AD configuration (see [Azure Setup](azure-setup.md))
2. Check redirect URI matches: `http://localhost:8000/auth/callback`
3. Ensure `.env` file is in `backend/` directory
4. Restart backend after `.env` changes

### ChromaDB Errors

Reset the vector store:
```bash
rm -rf ./data/chroma
```

### Python Version Issues

Verify Python version:
```bash
python --version  # Should be 3.11+
```

Consider using pyenv for version management.

### Node Version Issues

Verify Node version:
```bash
node --version  # Should be 18+
```

Consider using nvm for version management.

## Next Steps

1. [Configure Azure AD](azure-setup.md)
2. [Set environment variables](configuration.md)
3. [Deploy to production](deployment.md)
