# Personal AI Assistant

A powerful personal AI assistant that integrates with Microsoft 365, GitHub, Telegram, and more.

## Features

- **AI-Powered Chat** - Intelligent conversations with context from your data
- **Microsoft 365 Integration** - Access to OneDrive, Outlook, Calendar, To Do, and OneNote
- **RAG (Retrieval-Augmented Generation)** - AI responses enhanced with your notes
- **GitHub Integration** - Manage issues, PRs, and notifications
- **Telegram Integration** - Access your Telegram messages
- **Web Search** - Real-time web search capabilities
- **URL Fetching** - Read and analyze webpage content
- **Action Proposals** - AI suggests actions for your approval

## Quick Start

1. Clone the repository
2. Set up Azure AD app registration
3. Configure environment variables
4. Install dependencies
5. Run the application

See [Installation](getting-started/installation.md) for detailed instructions.

## Architecture

The application consists of:

- **Backend**: FastAPI (Python) with LangChain for AI
- **Frontend**: React with TypeScript
- **Vector Store**: ChromaDB for semantic search
- **LLM Providers**: Anthropic Claude, OpenAI, Google Gemini

## Security

The assistant includes built-in security measures:

- Prompt injection detection and filtering
- Rate limiting on sensitive endpoints
- Input validation and sanitization
- Security event logging

See [Security](architecture/security.md) for details.
