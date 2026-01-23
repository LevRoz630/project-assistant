# Development Setup

This guide covers setting up the development environment.

## Prerequisites

- Python 3.11+
- Node.js 18+
- Git
- An IDE (VS Code recommended)

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
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
```

### Install Dependencies

```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt  # Development dependencies
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

## IDE Configuration

### VS Code Extensions

Recommended extensions:
- Python
- Pylance
- ESLint
- Prettier
- Thunder Client (API testing)

### VS Code Settings

`.vscode/settings.json`:
```json
{
  "python.defaultInterpreterPath": "./backend/venv/bin/python",
  "python.formatting.provider": "black",
  "editor.formatOnSave": true,
  "[python]": {
    "editor.defaultFormatter": "ms-python.black-formatter"
  }
}
```

## Code Style

### Python

- Formatter: Black
- Linter: Ruff
- Type hints required

```bash
# Format
black backend/

# Lint
ruff check backend/
```

### TypeScript

- Formatter: Prettier
- Linter: ESLint

```bash
# Format
npm run format

# Lint
npm run lint
```

## Pre-commit Hooks

Install pre-commit hooks:

```bash
pip install pre-commit
pre-commit install
```

## Database

### ChromaDB

The vector store is file-based and persists to `./data/chroma/`.

To reset:
```bash
rm -rf ./data/chroma
```

## Debugging

### Backend Debugging

VS Code launch configuration:

```json
{
  "name": "FastAPI",
  "type": "python",
  "request": "launch",
  "module": "uvicorn",
  "args": ["main:app", "--reload"],
  "cwd": "${workspaceFolder}/backend"
}
```

### API Testing

Use the built-in Swagger UI at http://localhost:8000/docs

Or Thunder Client / Postman for API testing.
