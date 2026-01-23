# Architecture Overview

The Personal AI Assistant is built with a modern, modular architecture.

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Frontend (React)                       │
│                   http://localhost:5173                     │
└─────────────────────────┬───────────────────────────────────┘
                          │ HTTP/WebSocket
┌─────────────────────────▼───────────────────────────────────┐
│                    FastAPI Backend                          │
│                   http://localhost:8000                     │
├─────────────────────────────────────────────────────────────┤
│  Routers          │  Services            │  Integrations    │
│  ├─ auth.py       │  ├─ ai.py           │  ├─ Microsoft    │
│  ├─ chat.py       │  ├─ prompts.py      │  │   Graph API   │
│  ├─ notes.py      │  ├─ sanitization.py │  ├─ GitHub API   │
│  ├─ tasks.py      │  ├─ search.py       │  ├─ Telegram     │
│  ├─ calendar.py   │  ├─ web_fetch.py    │  └─ DuckDuckGo   │
│  ├─ email.py      │  ├─ vectors.py      │                   │
│  ├─ github.py     │  ├─ security.py     │                   │
│  └─ telegram.py   │  └─ prompt_config.py│                   │
└─────────────────────────────────────────────────────────────┘
          │                    │                    │
          ▼                    ▼                    ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────────┐
│   ChromaDB   │    │   LangChain  │    │  External APIs   │
│ Vector Store │    │   LLM Layer  │    │                  │
└──────────────┘    └──────────────┘    └──────────────────┘
```

## Directory Structure

```
project-assistant/
├── backend/
│   ├── main.py              # FastAPI app entry point
│   ├── config.py            # Environment configuration
│   ├── auth.py              # OAuth authentication
│   ├── prompt_config.yaml   # Admin prompt customization
│   ├── routers/             # API endpoint handlers
│   │   ├── chat.py
│   │   ├── notes.py
│   │   ├── tasks.py
│   │   └── ...
│   └── services/            # Business logic
│       ├── ai.py            # LLM orchestration
│       ├── prompts.py       # Role-based prompts
│       ├── sanitization.py  # Security utilities
│       ├── vectors.py       # ChromaDB integration
│       └── ...
├── frontend/
│   └── src/
│       ├── components/
│       └── ...
├── docs/                    # Documentation (this site)
├── tests/                   # Test suite
└── data/                    # Persistent data
    ├── chroma/              # Vector store
    └── telegram_session/    # Telegram auth
```

## Key Components

### LLM Integration

Uses LangChain for LLM abstraction:

- **Providers**: Anthropic, OpenAI, Google Gemini
- **Chains**: Prompt → LLM → Response
- **Streaming**: SSE for real-time responses

### Vector Store (RAG)

ChromaDB for semantic search:

- **Embeddings**: OpenAI text-embedding-3-small
- **Chunking**: 1000 tokens with 200 overlap
- **Search**: Top-k similarity search

### Authentication

Microsoft OAuth 2.0:

- Multi-account support
- Session-based authorization
- Automatic token refresh

### Role-Based Prompts

Specialized prompts for different tasks:

- Automatic role detection
- Context injection
- Admin customization via YAML

## Data Flow

### Chat Request Flow

1. **Input** → User sends message
2. **Validation** → Input validated and checked for injection
3. **Role Detection** → Appropriate AI role selected
4. **Context Gathering** → Notes, tasks, calendar, email fetched
5. **Sanitization** → All context sanitized
6. **LLM Generation** → Response generated with context
7. **Post-Processing** → SEARCH/FETCH blocks processed
8. **Action Parsing** → Proposed actions extracted
9. **Response** → Cleaned response returned

### Action Approval Flow

1. AI proposes action in response
2. Action stored as pending
3. User reviews and approves/rejects
4. If approved, action executed against external service
5. Status updated
