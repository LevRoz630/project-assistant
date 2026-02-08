# Personal AI Assistant

A unified web application for personal productivity with AI chat, RAG, and integrations with Microsoft 365, GitHub, Telegram, and more.

## Overview

The Personal AI Assistant helps you:

- Chat with AI that has context from your notes, tasks, calendar, and email
- Manage notes synced with OneDrive
- Track tasks via Microsoft To Do
- View and create calendar events
- Search and read emails
- Manage GitHub issues and pull requests
- Access Telegram messages
- Get daily research paper digests from arXiv
- Search the web and analyze webpages

## Key Features

### Multi-Provider LLM Support

Choose your preferred AI provider:

- **Anthropic Claude** - Claude 3.5 Sonnet, Haiku, Opus
- **OpenAI GPT** - GPT-4, GPT-3.5
- **Google Gemini** - Gemini 1.5 Pro, Flash

Configure via `DEFAULT_LLM_PROVIDER` environment variable.

### RAG (Retrieval-Augmented Generation)

The AI uses your personal data as context:

- Notes from OneDrive
- Task lists
- Calendar events
- Email inbox

Data is indexed in ChromaDB for semantic search.

### Microsoft 365 Integration

Full integration with Microsoft services via Azure AD OAuth:

- OneDrive file sync
- Outlook email and calendar
- Microsoft To Do tasks
- OneNote notebooks

### External Integrations

- **GitHub** - Issues, PRs, notifications, search
- **Telegram** - Messages and chats (via Telethon)
- **ArXiv** - Daily research paper digests

### Security

Built-in security measures:

- Prompt injection detection and filtering
- Input validation and sanitization
- Rate limiting
- Secure session management
- CORS configuration

See [Security](architecture/security.md) for details.

## Quick Start

1. [Install prerequisites](getting-started/installation.md)
2. [Set up Azure AD](getting-started/azure-setup.md)
3. [Configure environment](getting-started/configuration.md)
4. Run the application

## Architecture

```
Frontend (React)
    |
    v
FastAPI Backend
    |
    +---> Microsoft Graph API (M365)
    |
    +---> LangChain + ChromaDB (Vector Store)
    |
    +---> LLM Providers (Anthropic/OpenAI/Google)
    |
    +---> External APIs (GitHub, Telegram, ArXiv)
```

### Components

- **Backend**: FastAPI (Python 3.11+) with LangChain
- **Frontend**: React with TypeScript
- **Vector Store**: ChromaDB for embeddings
- **Deployment**: Docker, Railway

## Deployment Options

### Local Development

```bash
# Backend
cd backend && uvicorn main:app --reload

# Frontend
cd frontend && npm run dev
```

### Docker Compose

```bash
docker-compose up --build
```

## Documentation

- **Getting Started**
  - [Installation](getting-started/installation.md)
  - [Configuration](getting-started/configuration.md)
  - [Azure Setup](getting-started/azure-setup.md)
  - [Deployment](getting-started/deployment.md)

- **Features**
  - [AI Chat](features/ai-chat.md)
  - [Notes](features/notes.md)
  - [Tasks](features/tasks.md)
  - [Calendar](features/calendar.md)
  - [Email](features/email.md)
  - [GitHub](features/github.md)
  - [Telegram](features/telegram.md)
  - [Web Search](features/web-search.md)
  - [ArXiv Digest](features/arxiv.md)

- **Architecture**
  - [Overview](architecture/overview.md)
  - [Security](architecture/security.md)

- **Development**
  - [Setup](development/setup.md)
  - [Testing](development/testing.md)

- **API Reference**
  - [Overview](api/overview.md)
  - [Authentication](api/authentication.md)
  - [Chat](api/chat.md)
