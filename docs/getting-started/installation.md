# Installation

## Prerequisites

- Python 3.11+
- Node.js 18+
- Git

## Clone Repository

```bash
git clone https://github.com/your-org/project-assistant.git
cd project-assistant
```

## Backend Setup

1. Create a virtual environment:

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Copy environment template:

```bash
cp .env.example .env
```

4. Configure `.env` file (see [Configuration](configuration.md))

5. Run the backend:

```bash
uvicorn main:app --reload
```

## Frontend Setup

1. Install dependencies:

```bash
cd frontend
npm install
```

2. Run the development server:

```bash
npm run dev
```

## Verify Installation

1. Open http://localhost:5173 in your browser
2. Click "Login with Microsoft"
3. Authorize the application
4. Start chatting with your AI assistant

## Troubleshooting

### Common Issues

**Port already in use**
```bash
# Kill process on port 8000
lsof -i :8000 | xargs kill
```

**Missing dependencies**
```bash
pip install -r requirements.txt --upgrade
```

**Azure authentication fails**
- Verify your Azure AD configuration
- Check redirect URI matches your setup
- See [Azure Setup](azure-setup.md) for details
