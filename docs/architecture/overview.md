# Architecture Overview

The Personal AI Assistant is built with a modern, modular architecture designed for extensibility and security.

## System Architecture

```
                          ┌─────────────────────────────────────────┐
                          │            Frontend (React)             │
                          │         http://localhost:5173           │
                          └───────────────────┬─────────────────────┘
                                              │ HTTP / SSE
┌─────────────────────────────────────────────▼─────────────────────────────────────────────┐
│                                    FastAPI Backend                                         │
│                                 http://localhost:8000                                      │
├───────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                           │
│  ┌─────────────┐    ┌─────────────────┐    ┌─────────────────────────────────────────┐   │
│  │   Routers   │    │    Services     │    │             Integrations                │   │
│  ├─────────────┤    ├─────────────────┤    ├─────────────────────────────────────────┤   │
│  │ auth.py     │    │ ai.py           │    │ Microsoft Graph API                     │   │
│  │ chat.py     │    │ prompts.py      │    │   - OneDrive, Outlook, To Do, OneNote   │   │
│  │ notes.py    │    │ sanitization.py │    │                                         │   │
│  │ tasks.py    │    │ search.py       │    │ LLM Providers                           │   │
│  │ calendar.py │    │ web_fetch.py    │    │   - Anthropic (Claude)                  │   │
│  │ email.py    │    │ vectors.py      │    │   - OpenAI (GPT)                        │   │
│  │ github.py   │    │ security.py     │    │   - Google (Gemini)                     │   │
│  │ telegram.py │    │ github.py       │    │                                         │   │
│  │ arxiv.py    │    │ telegram.py     │    │ External APIs                           │   │
│  │ actions.py  │    │ arxiv.py        │    │   - GitHub, Telegram, ArXiv, DuckDuckGo │   │
│  │ sync.py     │    │ actions.py      │    │                                         │   │
│  └─────────────┘    └─────────────────┘    └─────────────────────────────────────────┘   │
│                                                                                           │
└───────────────────────────────────────────────────────────────────────────────────────────┘
            │                    │                    │
            ▼                    ▼                    ▼
  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
  │     ChromaDB     │  │    LangChain     │  │   File Storage   │
  │   Vector Store   │  │    LLM Layer     │  │   ./data/        │
  └──────────────────┘  └──────────────────┘  └──────────────────┘
```

## Directory Structure

```
project-assistant/
├── backend/
│   ├── main.py              # FastAPI app entry point
│   ├── config.py            # Environment configuration (pydantic-settings)
│   ├── auth.py              # Microsoft OAuth authentication
│   ├── prompt_config.yaml   # Admin-configurable prompts
│   ├── routers/             # API endpoint handlers
│   │   ├── chat.py          # AI chat with streaming
│   │   ├── notes.py         # OneDrive notes CRUD
│   │   ├── tasks.py         # Microsoft To Do
│   │   ├── calendar.py      # Outlook calendar
│   │   ├── email.py         # Outlook email
│   │   ├── github.py        # GitHub issues/PRs
│   │   ├── telegram.py      # Telegram messages
│   │   ├── arxiv.py         # ArXiv paper digest
│   │   ├── onenote.py       # OneNote integration
│   │   ├── actions.py       # AI action approval
│   │   └── sync.py          # Background sync
│   └── services/            # Business logic
│       ├── ai.py            # LLM orchestration
│       ├── prompts.py       # Role-based system prompts
│       ├── sanitization.py  # Prompt injection defense
│       ├── search.py        # DuckDuckGo web search
│       ├── web_fetch.py     # URL content fetching
│       ├── vectors.py       # ChromaDB operations
│       ├── security.py      # Rate limiting, logging
│       ├── graph.py         # Microsoft Graph client
│       ├── github.py        # GitHub API client
│       ├── telegram.py      # Telegram API client
│       ├── arxiv.py         # ArXiv fetch and ranking
│       └── actions.py       # Action management
├── frontend/
│   └── src/
│       ├── App.jsx
│       └── components/      # React UI components
├── tests/
│   ├── routers/             # Router unit tests
│   ├── services/            # Service unit tests
│   └── integration/         # Live API tests
├── docs/                    # MkDocs documentation
├── data/                    # Persistent data (created at runtime)
│   ├── chroma/              # Vector store database
│   ├── arxiv/digests/       # ArXiv digest JSON files
│   └── telegram_session/    # Telegram auth session
├── .env.example             # Environment template
├── requirements.txt         # Python dependencies
├── docker-compose.yml       # Development containers
├── Dockerfile               # Production container
├── Dockerfile.dev           # Development container
├── nginx.conf               # Production nginx config
└── Makefile                 # Development commands
```

## Key Components

### Multi-Provider LLM Integration

Uses LangChain for unified LLM access:

- **Providers**: Anthropic Claude, OpenAI GPT, Google Gemini
- **Selection**: `DEFAULT_LLM_PROVIDER` environment variable
- **Streaming**: Server-Sent Events (SSE) for real-time responses
- **Models**:
  - Anthropic: claude-sonnet-4, claude-3-haiku, claude-3-opus
  - OpenAI: gpt-4, gpt-4-turbo, gpt-3.5-turbo
  - Google: gemini-1.5-pro, gemini-1.5-flash

### Vector Store (RAG)

ChromaDB for semantic search and context retrieval:

- **Embeddings**: OpenAI text-embedding-3-small
- **Chunking**: 1000 tokens with 200 overlap
- **Search**: Top-k similarity search (default k=5)
- **Sources**: Notes, synced from OneDrive
- **Persistence**: `./data/chroma/`

### Authentication

Microsoft OAuth 2.0 via MSAL:

- **Flow**: Authorization code with PKCE
- **Scopes**: User.Read, Files.ReadWrite.All, Tasks.ReadWrite, etc.
- **Sessions**: Cookie-based, httponly
- **Multi-account**: Supports multiple Microsoft accounts
- **Token refresh**: Automatic before expiration

### Role-Based Prompts

Context-aware system prompts:

- **Roles**: general, email, tasks, calendar, github
- **Detection**: Automatic based on message content
- **Context injection**: Relevant data added to prompt
- **Customization**: `prompt_config.yaml` for admin changes

### Security Layer

Multiple defense mechanisms:

- **Prompt injection detection**: Pattern matching + unicode normalization
- **Input validation**: Length limits, content filtering
- **Rate limiting**: In-memory (Redis recommended for production)
- **Output sanitization**: Action parsing, content filtering
- **URL validation**: Blocked domains for fetch

## Data Flow

### Chat Request Flow

```
1. User Message
       │
       ▼
2. Input Validation
   - Length check (max 10,000 chars)
   - Prompt injection detection
       │
       ▼
3. Role Detection
   - Analyze message content
   - Select appropriate role/prompt
       │
       ▼
4. Context Gathering
   - RAG: Search vector store
   - Microsoft 365: Tasks, calendar, email
   - History: Previous messages
       │
       ▼
5. Content Sanitization
   - Truncate to limits
   - Remove injection patterns
   - Normalize unicode
       │
       ▼
6. LLM Generation
   - Build system prompt
   - Stream response via SSE
       │
       ▼
7. Post-Processing
   - Execute SEARCH blocks
   - Execute FETCH blocks
   - Re-generate if needed
       │
       ▼
8. Action Parsing
   - Extract TASK/EVENT/NOTE blocks
   - Store as pending actions
       │
       ▼
9. Response
   - Clean markdown
   - Include action IDs
```

### Action Approval Flow

```
1. AI proposes action in response
       │
       ▼
2. Action stored as pending
   - Type: task, event, note
   - Payload: title, body, date, etc.
       │
       ▼
3. User reviews in UI
       │
       ├──▶ Approve ──▶ Execute against service ──▶ Mark complete
       │
       └──▶ Reject ──▶ Mark rejected
```

### Web Search Flow

```
1. AI detects need for current info
       │
       ▼
2. Outputs SEARCH block
   ```SEARCH
   query here
   ```
       │
       ▼
3. System intercepts, queries DuckDuckGo
       │
       ▼
4. Results added to context
       │
       ▼
5. AI re-generates with search results
```

## Deployment Architecture

### Development (Docker Compose)

```
┌─────────────────────────────────────────┐
│           docker-compose                │
│  ┌─────────────────┐  ┌──────────────┐  │
│  │    backend      │  │   frontend   │  │
│  │   (uvicorn)     │  │    (vite)    │  │
│  │   port 8000     │  │  port 5173   │  │
│  └─────────────────┘  └──────────────┘  │
└─────────────────────────────────────────┘
```

### Production (Railway)

```
┌─────────────────────────────────────────────────────────────┐
│                     Railway Service                          │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                    nginx (:8080)                     │   │
│  │  ┌──────────────┐  ┌──────────────────────────────┐  │   │
│  │  │ Static files │  │  Proxy /api/ and /auth/      │  │   │
│  │  │ /frontend/   │  │  to localhost:8000           │  │   │
│  │  └──────────────┘  └──────────────────────────────┘  │   │
│  └─────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              uvicorn backend (:8000)                │   │
│  └─────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │         Persistent Volume (/app/data)               │   │
│  │         - ChromaDB, ArXiv digests                   │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## Technology Stack

| Layer | Technology |
|-------|------------|
| Frontend | React, TypeScript, Vite |
| Backend | FastAPI, Python 3.11+, Pydantic |
| LLM | LangChain, Anthropic/OpenAI/Google SDKs |
| Vector Store | ChromaDB |
| Auth | MSAL (Microsoft), OAuth 2.0 |
| HTTP Client | httpx, PyGithub, Telethon |
| Web Scraping | BeautifulSoup, DuckDuckGo-Search |
| Deployment | Docker, Railway, nginx |
| Testing | pytest, Vitest |
