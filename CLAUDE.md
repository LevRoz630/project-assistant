# Project Assistant

Personal AI assistant integrating Microsoft 365 (OneDrive, Outlook, To Do) with multi-provider LLM chat and RAG-powered context from your notes.
Aim of the project is to develop a scalable tool for human attention and planning. To create a distraction free environment where a user would be able to create through minimizing the aimless interactions.

## Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | FastAPI, Python 3.11+, MSAL, LangChain, ChromaDB |
| Frontend | React 18, Vite, React Router |
| Auth | Microsoft OAuth 2.0, multi-account support |
| LLM | Anthropic Claude (default), OpenAI, Google Gemini |
| Vector DB | ChromaDB with HuggingFace embeddings |
| External | Microsoft Graph API, GitHub, Telegram, ArXiv |

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Frontend (React + Vite)                   │
│  Components: Chat, Notes, Tasks, Calendar, Email, Actions   │
└──────────────────────────┬──────────────────────────────────┘
                           │ HTTP/CORS (session cookie)
┌──────────────────────────▼──────────────────────────────────┐
│                    FastAPI Backend                           │
│  Routers: auth, chat, notes, tasks, calendar, email, etc.   │
│  Services: ai, graph, vectors, sync, actions, security      │
└───────┬──────────────┬──────────────┬──────────────┬────────┘
        │              │              │              │
        ▼              ▼              ▼              ▼
   Microsoft       LLM APIs      ChromaDB       External
   Graph API       (Claude/      (Vectors)      APIs
   (M365 data)     GPT/Gemini)                  (GitHub, etc.)
```

## Directory Structure

```
backend/
├── main.py              # FastAPI app, middleware, static files
├── auth.py              # OAuth flow, multi-account, Redis/memory tokens
├── config.py            # Pydantic settings from .env
├── routers/
│   ├── chat.py          # AI chat with RAG, streaming, web search
│   ├── notes.py         # OneDrive markdown notes CRUD
│   ├── tasks.py         # Microsoft To Do integration
│   ├── calendar.py      # Outlook calendar events
│   ├── email.py         # Email inbox/search
│   ├── actions.py       # AI-proposed actions approval
│   ├── github.py        # GitHub repos, issues, PRs
│   ├── telegram.py      # Telegram messages
│   └── arxiv.py         # Research paper digest
└── services/
    ├── ai.py            # LLM instantiation, response generation
    ├── graph.py         # Microsoft Graph API client (GraphClient class)
    ├── vectors.py       # ChromaDB operations, semantic search
    ├── sync.py          # OneDrive -> vector store sync
    ├── actions.py       # ProposedAction management
    ├── sanitization.py  # Prompt injection detection
    └── prompts.py       # Role-based system prompts

frontend/src/
├── App.jsx              # Main shell, routing, auth check
├── components/
│   ├── Chat.jsx         # AI chat interface, streaming
│   ├── Notes.jsx        # Note browser
│   ├── NoteEditor.jsx   # Markdown editor with auto-save
│   ├── Tasks.jsx        # To Do lists
│   ├── Calendar.jsx     # Event viewer
│   ├── Email.jsx        # Inbox browser
│   └── Actions.jsx      # Pending action approvals
```

## Key Routers

| Router | Prefix | Purpose |
|--------|--------|---------|
| auth | /auth | OAuth login/callback/logout, multi-account |
| chat | /chat | AI responses with RAG, streaming, web search |
| notes | /notes | OneDrive markdown notes CRUD |
| tasks | /tasks | Microsoft To Do lists and items |
| calendar | /calendar | Outlook calendar events |
| email | /email | Inbox, folders, search |
| actions | /actions | AI-proposed action approval workflow |

## Key Services

| Service | Purpose |
|---------|---------|
| `ai.py` | Creates LLM instances (Claude/GPT/Gemini), generates responses |
| `graph.py` | `GraphClient` class for all Microsoft Graph API calls |
| `vectors.py` | ChromaDB operations: ingest, search, delete documents |
| `sync.py` | Delta sync from OneDrive to vector store |
| `actions.py` | Stores/executes proposed actions (tasks, events, notes) |
| `sanitization.py` | Detects prompt injection attempts |

## Authentication Flow

1. User hits `/auth/login` (or `/auth/login/email`, `/auth/login/storage`)
2. Redirect to Microsoft with OAuth scopes based on account purpose
3. Callback exchanges code for token via MSAL
4. Token stored in Redis (production) or memory (dev)
5. Session cookie (`session_id`) set for 7 days
6. `get_access_token_for_service(session_id, service)` retrieves appropriate token

**Multi-account purposes:**
- `primary` - All services (default)
- `email` - Email + Calendar only
- `storage` - OneDrive + To Do only

## Data Flows

### Chat with RAG
```
User message → /chat/stream →
  1. Get token for session
  2. Fetch context (notes from ChromaDB, calendar, tasks, email)
  3. Optional: web search, URL fetch
  4. Build prompt with context + role
  5. Stream response from LLM
  6. Parse any ACTION blocks → create ProposedAction
  7. Return streamed response
```

### Notes CRUD
```
Create/Update note → /notes/create or /notes/update →
  1. Auth check (get storage token)
  2. Write to OneDrive via Graph API
  3. Ingest to ChromaDB for RAG
  4. Return success
```

### AI Actions
```
LLM generates ACTION JSON → parsed in chat.py →
  Create ProposedAction (pending) →
  Frontend shows in Actions.jsx →
  User approves → /actions/{id}/approve →
  Execute action (create task/event/note) →
  Mark as approved
```

## Environment Variables

**Required:**
```
AZURE_CLIENT_ID=         # Azure AD app registration
AZURE_CLIENT_SECRET=     # OAuth client secret
AZURE_REDIRECT_URI=      # e.g., https://yourapp.com/auth/callback
SECRET_KEY=              # Session encryption
ANTHROPIC_API_KEY=       # Or OPENAI_API_KEY / GOOGLE_API_KEY
```

**Optional:**
```
DEFAULT_LLM_PROVIDER=anthropic    # anthropic, openai, google
DEFAULT_MODEL=claude-sonnet-4-20250514
REDIS_URL=                        # For persistent token storage
FRONTEND_URL=http://localhost:5173
ONEDRIVE_BASE_FOLDER=PersonalAI
GITHUB_TOKEN=                     # For GitHub integration
TELEGRAM_API_ID=                  # For Telegram integration
```

## Development

```bash
make dev          # Run backend + frontend with hot reload
make backend      # Backend only (uvicorn --reload)
make frontend     # Frontend only (vite dev)
make test         # Run pytest
make lint         # Run ruff linter
make format       # Format code
```

## Common Patterns

**Getting authenticated Graph client:**
```python
from backend.services.graph import GraphClient
from backend.auth import get_access_token_for_service

token = get_access_token_for_service(session_id, "calendar")
client = GraphClient(token)
events = await client.get_calendar_view(start, end)
```

**Adding a new router:**
1. Create `backend/routers/myrouter.py`
2. Define `router = APIRouter(prefix="/myroute", tags=["myroute"])`
3. Add to `backend/main.py`: `app.include_router(myrouter.router)`

**Vector search for RAG:**
```python
from backend.services.vectors import search_documents
results = search_documents(query="meeting notes", top_k=5)
```
