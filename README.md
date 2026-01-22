# Personal AI Assistant

A unified web application for personal productivity: AI chat with RAG, notes/diary, tasks, and calendar — all integrated with Microsoft 365.

## Features

- **AI Chat** - Conversational AI with RAG from notes, tasks, calendar, and email context
- **Notes** - Markdown notes synced with OneDrive (Diary, Projects, Study, Inbox)
- **Tasks** - Microsoft To Do integration with full CRUD
- **Calendar** - Outlook calendar view and event creation
- **Email** - Email inbox viewing and search
- **AI Actions** - AI can propose tasks, events, and notes for user approval
- **Auto-Sync** - Background syncing of notes to vector store for RAG

## Architecture

```
Frontend (React) → FastAPI Backend → Microsoft Graph API
                        ↓
                  LangChain + ChromaDB
```

## Prerequisites

- Python 3.11+
- Node.js 18+
- Microsoft Azure account (for OAuth app registration)
- Anthropic or OpenAI API key

## Azure AD Setup

1. Go to [Azure Portal](https://portal.azure.com)
2. Navigate to **Azure Active Directory** → **App registrations** → **New registration**
3. Configure:
   - Name: `Personal AI Assistant`
   - Supported account types: `Accounts in any organizational directory and personal Microsoft accounts`
   - Redirect URI: `Web` → `http://localhost:8000/auth/callback`
4. After creation, note the **Application (client) ID**
5. Go to **Certificates & secrets** → **New client secret** → Copy the secret value
6. Go to **API permissions** → **Add a permission** → **Microsoft Graph** → **Delegated permissions**:
   - `User.Read`
   - `Files.ReadWrite.All`
   - `Tasks.ReadWrite`
   - `Calendars.ReadWrite`
   - `Mail.Read`
7. Click **Grant admin consent** (if you have admin rights)

## Quick Start

### 1. Clone and configure

```bash
git clone <repo-url>
cd project-assistant
cp .env.example .env
# Edit .env with your credentials
```

### 2. Backend Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r ../requirements.txt
```

### 3. Frontend Setup

```bash
cd frontend
npm install
```

### 4. Run Development Servers

Terminal 1 (Backend):
```bash
cd backend
uvicorn main:app --reload
```

Terminal 2 (Frontend):
```bash
cd frontend
npm run dev
```

Open http://localhost:5173 in your browser.

## Docker Setup

```bash
docker-compose up --build
```

## Project Structure

```
project-assistant/
├── backend/
│   ├── main.py              # FastAPI entry point
│   ├── auth.py              # Microsoft OAuth
│   ├── config.py            # Settings
│   ├── routers/
│   │   ├── chat.py          # AI chat endpoints
│   │   ├── notes.py         # Notes CRUD
│   │   ├── tasks.py         # To Do integration
│   │   ├── calendar.py      # Calendar endpoints
│   │   ├── email.py         # Email endpoints
│   │   ├── sync.py          # Auto-sync endpoints
│   │   └── actions.py       # AI actions/approval endpoints
│   └── services/
│       ├── graph.py         # Microsoft Graph client
│       ├── ai.py            # LangChain setup
│       ├── vectors.py       # ChromaDB operations
│       ├── sync.py          # OneDrive sync service
│       └── actions.py       # Action management service
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   └── components/
│   │       ├── Chat.jsx
│   │       ├── Notes.jsx
│   │       ├── NoteEditor.jsx
│   │       ├── Tasks.jsx
│   │       ├── Calendar.jsx
│   │       ├── Email.jsx
│   │       ├── Actions.jsx
│   │       └── Accounts.jsx
│   └── package.json
├── requirements.txt
├── docker-compose.yml
└── .env.example
```

## OneDrive Folder Structure

The app creates this structure in your OneDrive:

```
OneDrive/
└── PersonalAI/
    ├── Diary/          # Daily diary entries
    ├── Projects/       # Project notes
    ├── Study/          # Study notes
    └── Inbox/          # Quick notes
```

## API Endpoints

### Auth
- `GET /auth/login` - Initiate Microsoft OAuth
- `GET /auth/callback` - OAuth callback
- `GET /auth/logout` - Log out
- `GET /auth/me` - Get current user

### Chat
- `POST /chat/send` - Send message, get response
- `POST /chat/stream` - Stream response (SSE)
- `POST /chat/ingest` - Re-index all notes

### Notes
- `GET /notes/folders` - List folders
- `GET /notes/list/{folder}` - List notes in folder
- `GET /notes/content/{folder}/{filename}` - Get note content
- `POST /notes/create` - Create note
- `PUT /notes/update/{folder}/{filename}` - Update note
- `DELETE /notes/delete/{folder}/{filename}` - Delete note
- `POST /notes/diary/today` - Create/get today's diary

### Tasks
- `GET /tasks/lists` - List task lists
- `GET /tasks/list/{list_id}` - List tasks
- `GET /tasks/all` - All tasks from all lists
- `POST /tasks/create` - Create task
- `POST /tasks/complete/{list_id}/{task_id}` - Complete task
- `DELETE /tasks/delete/{list_id}/{task_id}` - Delete task

### Calendar
- `GET /calendar/list` - List calendars
- `GET /calendar/today` - Today's events
- `GET /calendar/week` - This week's events
- `POST /calendar/create` - Create event
- `DELETE /calendar/delete/{event_id}` - Delete event

### Email
- `GET /email/inbox` - Get inbox messages
- `GET /email/message/{id}` - Get specific email
- `GET /email/search` - Search emails
- `GET /email/folders` - List mail folders

### Sync
- `GET /sync/status` - Get sync status
- `POST /sync/now` - Trigger immediate sync
- `POST /sync/scheduler/start` - Start background sync
- `POST /sync/scheduler/stop` - Stop background sync

### Actions
- `GET /actions/pending` - List pending AI actions
- `GET /actions/history` - List action history
- `POST /actions/create` - Create proposed action
- `POST /actions/{id}/approve` - Approve and execute action
- `POST /actions/{id}/reject` - Reject action

## Environment Variables

| Variable | Description |
|----------|-------------|
| `AZURE_CLIENT_ID` | Azure AD application ID |
| `AZURE_CLIENT_SECRET` | Azure AD client secret |
| `AZURE_TENANT_ID` | `common` for personal accounts |
| `ANTHROPIC_API_KEY` | Anthropic API key (for Claude) |
| `OPENAI_API_KEY` | OpenAI API key (for embeddings + optional LLM) |
| `DEFAULT_LLM_PROVIDER` | `anthropic` or `openai` |
| `ONEDRIVE_BASE_FOLDER` | Base folder in OneDrive (default: `PersonalAI`) |

## Development

### Testing

**Backend Tests (pytest):**
```bash
# Run all tests
make test

# Run with coverage
make test-cov

# Run specific test file
cd backend && python -m pytest ../tests/services/test_actions.py -v
```

**Frontend Tests (Vitest):**
```bash
cd frontend
npm test              # Run tests in watch mode
npm run test:coverage # Run with coverage
```

### Linting & Type Checking

```bash
# Lint Python code
make lint

# Fix lint issues
make lint-fix

# Format code
make format

# Type check
make type-check

# Run all checks
make check
```

### Pre-commit Hooks

```bash
# Install pre-commit hooks
make pre-commit

# Run on all files
make pre-commit-run
```

## Troubleshooting

### "unauthorized_client: The client does not exist or is not enabled for consumers"

This error occurs when signing in with a personal Microsoft account (@outlook.com, @hotmail.com) but the App Registration doesn't allow it.

**Fix:**
1. Go to Azure Portal → App registrations → your app
2. Click **Manifest** in the left sidebar
3. Find `"signInAudience"` and change it to:
   ```json
   "signInAudience": "AzureADandPersonalMicrosoftAccount"
   ```
4. Click **Save**

Note: Azure doesn't allow changing this via the UI for existing registrations - you must use the Manifest editor.

### "AADSTS900144: The request body must contain the following parameter: 'client_id'"

The backend can't find your Azure credentials.

**Fix:**
1. Ensure `.env` file exists in the `backend/` folder (not just the project root)
2. Verify `AZURE_CLIENT_ID` and `AZURE_CLIENT_SECRET` are set correctly
3. Restart the backend after any `.env` changes

### Sign-in redirects fail or loop

Check that your **Redirect URI** in Azure matches exactly:
1. Azure Portal → App registrations → your app → Authentication
2. Add platform: **Web**
3. Redirect URI: `http://localhost:8000/auth/callback`

## Development Roadmap

- [x] M1: Foundation (OAuth, basic UI)
- [x] M2: Notes & Diary
- [x] M3: AI Chat + RAG (with auto-sync)
- [x] M4: Tasks Integration (AI can read and propose tasks)
- [x] M5: Calendar & Email (Email UI, AI context)
- [x] M6: AI Actions & Approvals (approval workflow UI)
- [ ] M7: Agentic Workflows (LangGraph integration)

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Install dev dependencies: `pip install -e ".[dev]"` and `cd frontend && npm install`
4. Install pre-commit hooks: `make pre-commit`
5. Make your changes and ensure tests pass: `make check`
6. Submit a pull request

## License

MIT
