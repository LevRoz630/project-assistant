# Personal AI Assistant

A unified web application for personal productivity: AI chat with RAG, notes/diary, tasks, and calendar integrated with Microsoft 365. The goal is to minimize time spent on scrolling and useless information consumption.

## Features

### AI and Chat
- **Multi-Provider LLM Support** - Anthropic (Claude), OpenAI (GPT), and Google (Gemini) with configurable defaults
- **RAG (Retrieval-Augmented Generation)** - AI responses enhanced with context from your notes, tasks, calendar, and email
- **Web Search** - Real-time web search via DuckDuckGo
- **URL Fetching** - Read and analyze webpage content with BeautifulSoup
- **AI Actions** - AI can propose tasks, events, and notes for user approval

### Microsoft 365 Integration
- **Notes** - Markdown notes synced with OneDrive (Diary, Projects, Study, Inbox)
- **OneNote** - Full OneNote integration for mobile note-taking
- **Tasks** - Microsoft To Do integration with full CRUD
- **Calendar** - Outlook calendar view and event creation
- **Email** - Email inbox viewing and search

### External Integrations
- **GitHub** - Full GitHub integration (issues, PRs, repos, search, write operations)
- **Telegram** - Read Telegram messages and chats (optional, requires user API credentials)
- **ArXiv Digest** - Daily research paper digest with AI-powered relevance ranking

### Infrastructure
- **Vector Store** - ChromaDB for semantic search and embeddings
- **Auto-Sync** - Background syncing of notes to vector store
- **PWA** - Installable as a Progressive Web App on mobile
- **Security** - Prompt injection detection, rate limiting, input sanitization

## Architecture

```
Frontend (React) --> FastAPI Backend --> Microsoft Graph API
                          |
                          +--> LangChain + ChromaDB (Vector Store)
                          |
                          +--> LLM Providers (Anthropic/OpenAI/Google)
                          |
                          +--> External APIs (GitHub, Telegram, ArXiv)
```

## Prerequisites

- Python 3.11+
- Node.js 18+
- Microsoft Azure account (for OAuth app registration)
- At least one LLM API key: Anthropic, OpenAI, or Google

## Azure AD Setup

1. Go to [Azure Portal](https://portal.azure.com)
2. Navigate to **Azure Active Directory** -> **App registrations** -> **New registration**
3. Configure:
   - Name: `Personal AI Assistant`
   - Supported account types: `Accounts in any organizational directory and personal Microsoft accounts`
   - Redirect URI: `Web` -> `http://localhost:8000/auth/callback`
4. After creation, note the **Application (client) ID**
5. Go to **Certificates & secrets** -> **New client secret** -> Copy the secret value
6. Go to **API permissions** -> **Add a permission** -> **Microsoft Graph** -> **Delegated permissions**:
   - `User.Read`
   - `Files.ReadWrite.All`
   - `Tasks.ReadWrite`
   - `Calendars.ReadWrite`
   - `Mail.Read`
   - `Notes.ReadWrite` (for OneNote)
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

### Development with Docker Compose

Run both frontend and backend with hot reload:

```bash
docker-compose up --build
```

This starts:
- Backend at http://localhost:8000
- Frontend at http://localhost:5173

### Development Container

A full development container is available with Claude Code, Fly.io CLI, and GitHub CLI pre-installed:

```bash
# Build the dev container
docker build -f Dockerfile.dev -t project-assistant-dev .

# Run with your project mounted
docker run -it -v $(pwd):/workspace project-assistant-dev

# Inside the container:
# - claude: Claude Code CLI
# - flyctl: Fly.io CLI
# - gh: GitHub CLI
# - node/npm: Node.js 20
# - python3: Python 3.11
```

### Production Build

Build a single production image (frontend + backend + nginx):

```bash
docker build -f Dockerfile.fly -t project-assistant .
docker run -p 8080:8080 --env-file .env project-assistant
```

## Fly.io Deployment

### Initial Setup

1. Install the Fly.io CLI: https://fly.io/docs/hands-on/install-flyctl/

2. Authenticate:
```bash
flyctl auth login
```

3. Create the app (first time only):
```bash
flyctl apps create project-assistant
```

4. Create a persistent volume for ChromaDB:
```bash
flyctl volumes create chromadb_data --region lhr --size 1
```

5. Set secrets:
```bash
flyctl secrets set \
  AZURE_CLIENT_ID=your-client-id \
  AZURE_CLIENT_SECRET=your-client-secret \
  ANTHROPIC_API_KEY=your-api-key \
  SECRET_KEY=your-secret-key \
  GITHUB_TOKEN=your-token
```

### Deploy

```bash
flyctl deploy
```

The app will be available at `https://project-assistant.fly.dev`

### Configuration

The `fly.toml` configuration:

```toml
app = "project-assistant"
primary_region = "lhr"

[build]
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

### Update Azure Redirect URI

For production, add the Fly.io callback URL to your Azure AD app:
- `https://project-assistant.fly.dev/auth/callback`

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
│   │   ├── onenote.py       # OneNote integration
│   │   ├── tasks.py         # To Do integration
│   │   ├── calendar.py      # Calendar endpoints
│   │   ├── email.py         # Email endpoints
│   │   ├── github.py        # GitHub integration
│   │   ├── telegram.py      # Telegram integration
│   │   ├── sync.py          # Auto-sync endpoints
│   │   └── actions.py       # AI actions/approval endpoints
│   └── services/
│       ├── graph.py         # Microsoft Graph client
│       ├── ai.py            # LangChain setup
│       ├── vectors.py       # ChromaDB operations
│       ├── github.py        # GitHub API client
│       ├── telegram.py      # Telegram API client
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
├── tests/
│   ├── routers/             # Unit tests (mocked)
│   └── integration/         # Live API tests
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

### GitHub
- `GET /github/status` - Connection status
- `GET /github/repos` - List your repositories
- `GET /github/repos/{owner}/{repo}/branches` - List branches
- `GET /github/repos/{owner}/{repo}/labels` - List labels
- `GET /github/repos/{owner}/{repo}/collaborators` - List collaborators
- `GET /github/issues/assigned` - Issues assigned to you
- `GET /github/issues/created` - Issues you created
- `GET /github/issues/mentioned` - Issues mentioning you
- `GET /github/repos/{owner}/{repo}/issues/{num}` - Get specific issue
- `POST /github/repos/{owner}/{repo}/issues` - Create issue
- `PATCH /github/repos/{owner}/{repo}/issues/{num}` - Update issue
- `POST /github/repos/{owner}/{repo}/issues/{num}/close` - Close issue
- `POST /github/repos/{owner}/{repo}/issues/{num}/reopen` - Reopen issue
- `GET /github/repos/{owner}/{repo}/issues/{num}/comments` - Get comments
- `POST /github/repos/{owner}/{repo}/issues/{num}/comments` - Add comment
- `POST /github/repos/{owner}/{repo}/issues/{num}/labels` - Add labels
- `DELETE /github/repos/{owner}/{repo}/issues/{num}/labels` - Remove labels
- `POST /github/repos/{owner}/{repo}/issues/{num}/assignees` - Assign users
- `GET /github/prs/review-requests` - PRs awaiting your review
- `GET /github/prs/mine` - Your PRs
- `GET /github/repos/{owner}/{repo}/pulls/{num}` - Get specific PR
- `POST /github/repos/{owner}/{repo}/pulls` - Create PR
- `PUT /github/repos/{owner}/{repo}/pulls/{num}/merge` - Merge PR
- `POST /github/repos/{owner}/{repo}/pulls/{num}/requested_reviewers` - Request reviewers
- `POST /github/repos/{owner}/{repo}/pulls/{num}/reviews` - Add review
- `GET /github/search/issues` - Search issues/PRs
- `GET /github/search/repos` - Search repositories

### Telegram
- `GET /telegram/status` - Connection status
- `POST /telegram/auth/start` - Start authentication (sends code to phone)
- `POST /telegram/auth/complete` - Complete authentication with code
- `GET /telegram/dialogs` - List chats/dialogs
- `GET /telegram/unread` - Get unread messages
- `GET /telegram/messages/{chat_id}` - Get messages from chat
- `POST /telegram/messages/{chat_id}/read` - Mark as read
- `GET /telegram/summary` - Updates summary

### OneNote
- `GET /onenote/notebooks` - List notebooks
- `POST /onenote/notebooks` - Create notebook
- `GET /onenote/notebooks/{id}/sections` - List sections
- `POST /onenote/notebooks/{id}/sections` - Create section
- `GET /onenote/sections/{id}/pages` - List pages
- `GET /onenote/pages/{id}` - Get page content (as markdown)
- `POST /onenote/sections/{id}/pages` - Create page
- `PATCH /onenote/pages/{id}` - Update page
- `DELETE /onenote/pages/{id}` - Delete page
- `GET /onenote/diary/today` - Get/create today's diary page

### ArXiv
- `GET /arxiv/digest` - Get the most recent digest
- `GET /arxiv/digest/{date}` - Get digest for specific date (YYYY-MM-DD)
- `GET /arxiv/digests` - List available digest dates
- `GET /arxiv/status` - Get service status
- `POST /arxiv/run-now` - Trigger immediate digest generation
- `POST /arxiv/scheduler/start` - Start daily scheduler
- `POST /arxiv/scheduler/stop` - Stop scheduler
- `GET /arxiv/config` - Get current configuration
- `PUT /arxiv/config` - Update configuration (runtime only)

## Environment Variables

### Required

| Variable | Description |
|----------|-------------|
| `AZURE_CLIENT_ID` | Azure AD application ID |
| `AZURE_CLIENT_SECRET` | Azure AD client secret |
| `AZURE_TENANT_ID` | `common` for personal accounts |
| `AZURE_REDIRECT_URI` | OAuth callback URL (default: `http://localhost:8000/auth/callback`) |
| `SECRET_KEY` | Secret key for session encryption (change in production) |

### AI Providers (at least one required)

| Variable | Description |
|----------|-------------|
| `ANTHROPIC_API_KEY` | Anthropic API key (for Claude models) |
| `OPENAI_API_KEY` | OpenAI API key (for GPT models and embeddings) |
| `GOOGLE_API_KEY` | Google API key (for Gemini models) |
| `DEFAULT_LLM_PROVIDER` | `anthropic`, `openai`, or `google` |
| `DEFAULT_MODEL` | Model name (default: `claude-sonnet-4-20250514`) |

### OneDrive & Storage

| Variable | Description |
|----------|-------------|
| `ONEDRIVE_BASE_FOLDER` | Base folder in OneDrive (default: `PersonalAI`) |
| `CHROMA_PERSIST_DIRECTORY` | Vector store path (default: `./data/chroma`) |

### GitHub Integration

| Variable | Description |
|----------|-------------|
| `GITHUB_TOKEN` | GitHub Personal Access Token (fine-grained recommended) |
| `GITHUB_USERNAME` | Your GitHub username |

### Telegram Integration (optional)

| Variable | Description |
|----------|-------------|
| `TELEGRAM_API_ID` | Telegram API ID from https://my.telegram.org |
| `TELEGRAM_API_HASH` | Telegram API hash |
| `TELEGRAM_PHONE` | Your phone number with country code |
| `TELEGRAM_SESSION_PATH` | Session file path (default: `./data/telegram_session`) |

### ArXiv Digest

| Variable | Description |
|----------|-------------|
| `ARXIV_CATEGORIES` | Comma-separated arXiv categories (default: `cs.AI,cs.CL,cs.LG,q-fin.ST,stat.ML`) |
| `ARXIV_INTERESTS` | Research interests for paper ranking |
| `ARXIV_SCHEDULE_HOUR` | UTC hour for daily digest (default: `6`) |
| `ARXIV_MAX_PAPERS` | Max papers to fetch (default: `50`) |
| `ARXIV_TOP_N` | Top N papers in digest (default: `10`) |
| `ARXIV_LLM_PROVIDER` | LLM provider for ranking (default: `anthropic`) |

### Web Features

| Variable | Description |
|----------|-------------|
| `ENABLE_WEB_SEARCH` | Enable AI web search (default: `true`) |
| `ENABLE_URL_FETCH` | Enable AI URL fetching (default: `true`) |
| `FRONTEND_URL` | Frontend URL for CORS (default: `http://localhost:5173`) |

## GitHub Setup

1. Go to https://github.com/settings/tokens?type=beta (fine-grained tokens)
2. Click **Generate new token**
3. Set expiration and select repositories (or all)
4. Under **Repository permissions**, enable:
   - **Issues**: Read and write
   - **Pull requests**: Read and write
   - **Contents**: Read-only
   - **Metadata**: Read-only
5. Copy the token to `GITHUB_TOKEN` in `.env`

## Telegram Setup

1. Go to https://my.telegram.org and log in
2. Click **API development tools**
3. Create a new application
4. Copy **App api_id** to `TELEGRAM_API_ID`
5. Copy **App api_hash** to `TELEGRAM_API_HASH`
6. Set `TELEGRAM_PHONE` to your phone number (e.g., `+1234567890`)
7. On first use, call `POST /telegram/auth/start` then `POST /telegram/auth/complete` with the code sent to your phone

## ArXiv Digest Setup

The ArXiv digest feature fetches recent papers from specified categories and uses AI to rank them by relevance to your research interests.

### Configuration

Set in `.env`:

```bash
ARXIV_CATEGORIES=cs.AI,cs.CL,cs.LG,q-fin.ST,stat.ML
ARXIV_INTERESTS=AI agents, LLMs, NLP, quantitative finance, ML for trading
ARXIV_SCHEDULE_HOUR=6  # UTC hour for daily run
ARXIV_MAX_PAPERS=50    # Papers to fetch
ARXIV_TOP_N=10         # Top papers in digest
ARXIV_LLM_PROVIDER=anthropic  # anthropic, openai, or google
```

### Usage

```bash
# Get latest digest
GET /arxiv/digest

# Trigger manual digest generation
POST /arxiv/run-now

# Start daily scheduler
POST /arxiv/scheduler/start

# Stop scheduler
POST /arxiv/scheduler/stop

# Check status
GET /arxiv/status
```

### How It Works

1. Fetches recent papers from arXiv API for configured categories
2. Uses a fast LLM (Claude Haiku, GPT-3.5, or Gemini Flash) to score relevance
3. Returns top N papers ranked by relevance with explanations
4. Digests are saved to `./data/arxiv/digests/` as JSON files

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
