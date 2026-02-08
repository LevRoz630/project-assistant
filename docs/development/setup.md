# Development Setup

This guide covers setting up the development environment for contributing to the Personal AI Assistant.

## Prerequisites

- **Python 3.11+** - Backend runtime
- **Node.js 18+** - Frontend tooling
- **Git** - Version control
- **Docker** (optional) - Container development

Recommended:
- **VS Code** - IDE with excellent Python/TypeScript support
- **pre-commit** - Git hooks for code quality

## Clone Repository

```bash
git clone https://github.com/your-org/project-assistant.git
cd project-assistant
```

## Backend Setup

### Virtual Environment

```bash
cd backend
python -m venv venv

# Activate on Linux/Mac
source venv/bin/activate

# Activate on Windows
venv\Scripts\activate
```

### Install Dependencies

```bash
# Production dependencies
pip install -r requirements.txt

# Development dependencies (includes testing, linting)
pip install -e ".[dev]"
```

### Configure Environment

```bash
cp .env.example .env
# Edit .env with your credentials
```

### Run Backend

```bash
uvicorn main:app --reload --port 8000
```

The API will be at http://localhost:8000 with auto-reload on code changes.

### API Documentation

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Frontend Setup

### Install Dependencies

```bash
cd frontend
npm install
```

### Run Frontend

```bash
npm run dev
```

The app will be at http://localhost:5173 with hot module replacement.

## Docker Development

### Docker Compose

Run everything with hot reload:

```bash
docker-compose up --build
```

### Development Container

Use the full dev container with all tools:

```bash
docker build -f Dockerfile.dev -t project-assistant-dev .
docker run -it -v $(pwd):/workspace project-assistant-dev
```

Includes: Claude Code CLI, gh, Node.js 20, Python 3.11.

## IDE Configuration

### VS Code Extensions

Recommended extensions (`.vscode/extensions.json`):

- Python (ms-python.python)
- Pylance (ms-python.vscode-pylance)
- Black Formatter (ms-python.black-formatter)
- Ruff (charliermarsh.ruff)
- ESLint (dbaeumer.vscode-eslint)
- Prettier (esbenp.prettier-vscode)
- Thunder Client (rangav.vscode-thunder-client)

### VS Code Settings

Create `.vscode/settings.json`:

```json
{
  "python.defaultInterpreterPath": "./backend/venv/bin/python",
  "[python]": {
    "editor.defaultFormatter": "ms-python.black-formatter",
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
      "source.fixAll.ruff": "explicit",
      "source.organizeImports.ruff": "explicit"
    }
  },
  "[typescript]": {
    "editor.defaultFormatter": "esbenp.prettier-vscode",
    "editor.formatOnSave": true
  },
  "[typescriptreact]": {
    "editor.defaultFormatter": "esbenp.prettier-vscode",
    "editor.formatOnSave": true
  }
}
```

### VS Code Launch Configuration

Create `.vscode/launch.json`:

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "FastAPI Backend",
      "type": "debugpy",
      "request": "launch",
      "module": "uvicorn",
      "args": ["main:app", "--reload", "--port", "8000"],
      "cwd": "${workspaceFolder}/backend",
      "envFile": "${workspaceFolder}/.env"
    },
    {
      "name": "Python: Current File",
      "type": "debugpy",
      "request": "launch",
      "program": "${file}",
      "cwd": "${workspaceFolder}/backend"
    },
    {
      "name": "Pytest",
      "type": "debugpy",
      "request": "launch",
      "module": "pytest",
      "args": ["../tests", "-v"],
      "cwd": "${workspaceFolder}/backend"
    }
  ]
}
```

## Code Style

### Python

- **Formatter**: Ruff (Black-compatible)
- **Linter**: Ruff
- **Type checker**: mypy
- **Style**: PEP 8, type hints required

```bash
# Format code
make format
# or
ruff format backend tests

# Lint
make lint
# or
ruff check backend tests

# Fix lint issues
make lint-fix
# or
ruff check backend tests --fix

# Type check
make type-check
# or
cd backend && python -m mypy . --ignore-missing-imports
```

### TypeScript/JavaScript

- **Formatter**: Prettier
- **Linter**: ESLint

```bash
cd frontend

# Format
npm run format

# Lint
npm run lint

# Lint with fix
npm run lint:fix
```

## Pre-commit Hooks

Install hooks to run checks before each commit:

```bash
pip install pre-commit
pre-commit install
pre-commit install --hook-type commit-msg
```

Run on all files:

```bash
make pre-commit-run
# or
pre-commit run --all-files
```

## Make Commands

The Makefile provides shortcuts for common tasks:

```bash
make help          # Show all commands

# Setup
make install       # Install production deps
make install-dev   # Install dev deps

# Testing
make test          # Run tests
make test-cov      # Run tests with coverage
make test-watch    # Run tests in watch mode

# Code Quality
make lint          # Run linter
make lint-fix      # Fix lint issues
make format        # Format code
make type-check    # Run type checker
make check         # Run all checks

# Development
make backend       # Start backend
make frontend      # Start frontend
make dev           # Start both

# Docker
make docker-build  # Build containers
make docker-up     # Start containers
make docker-down   # Stop containers
make docker-logs   # View logs

# Cleanup
make clean         # Remove build artifacts
```

## Database/Storage

### ChromaDB

The vector store persists to `./data/chroma/`. To reset:

```bash
rm -rf ./data/chroma
```

### ArXiv Digests

Stored as JSON in `./data/arxiv/digests/`.

### Telegram Session

Session file at `./data/telegram_session`.

## Testing

See [Testing](testing.md) for detailed test documentation.

Quick start:

```bash
# Run all tests
make test

# Run with coverage
make test-cov

# Run specific test file
cd backend && python -m pytest ../tests/services/test_arxiv.py -v

# Run integration tests (requires API keys)
cd backend && python -m pytest ../tests/integration/ -v
```

## Debugging

### Backend Debugging

1. Use VS Code debugger with the FastAPI launch config
2. Set breakpoints in code
3. Check logs: `uvicorn` outputs to console

### Frontend Debugging

1. Use browser DevTools (F12)
2. React DevTools extension for component inspection
3. Check Network tab for API calls

### API Testing

1. Swagger UI at http://localhost:8000/docs
2. Thunder Client VS Code extension
3. curl or httpie

## Troubleshooting

### Import Errors

Ensure you're in the virtual environment:
```bash
which python  # Should show venv path
```

### Port Conflicts

Kill processes on ports:
```bash
lsof -i :8000  # Find backend process
lsof -i :5173  # Find frontend process
kill -9 <PID>
```

### Hot Reload Not Working

- Backend: Ensure `--reload` flag is set
- Frontend: Check Vite console for errors
- Docker: Ensure volumes are mounted correctly

### Type Errors

Run mypy to check:
```bash
cd backend && python -m mypy . --ignore-missing-imports
```

### Environment Variables Not Loading

1. Check `.env` file exists in correct location
2. Restart the server after changes
3. Verify variable names match `config.py`
