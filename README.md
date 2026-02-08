# Project Assistant

Personal productivity tool that ties together Microsoft 365 (OneDrive, Outlook, To Do) with LLM chat. Your notes, tasks, calendar and email feed into the AI as context so you get answers grounded in your own data instead of generic responses.

Built to cut down on aimless scrolling — one place to plan, write, and think.

## What it does

- **Chat** — Talk to Claude/GPT/Gemini with your notes and schedule as context (RAG). It can propose tasks, events, and notes that you approve before they're created.
- **Notes** — Markdown notes stored in OneDrive, organized in nested folders. Auto-synced to a vector store for search.
- **Tasks** — Microsoft To Do, full CRUD.
- **Calendar** — Outlook calendar view and event creation.
- **Email** — Read and search your inbox.
- **GitHub** — Issues, PRs, repos. Read and write.
- **Telegram** — Read your messages (optional, needs your own API creds).
- **ArXiv** — Daily digest of papers ranked by your interests.

## Stack

| | |
|---|---|
| Backend | FastAPI, Python 3.11+, MSAL |
| Frontend | React 18, Vite |
| Auth | Microsoft OAuth 2.0, multi-account |
| AI | LangChain + Anthropic / OpenAI / Google |
| Vector DB | ChromaDB with HuggingFace embeddings |
| External | Microsoft Graph API, GitHub, Telegram, ArXiv |

## Setup

### Prerequisites

- Python 3.11+
- Node.js 18+
- Azure AD app registration (for Microsoft OAuth)
- At least one LLM API key (Anthropic, OpenAI, or Google)

### Azure AD

1. [Azure Portal](https://portal.azure.com) → Azure Active Directory → App registrations → New registration
2. Supported account types: `Accounts in any organizational directory and personal Microsoft accounts`
3. Redirect URI: `Web` → `http://localhost:8000/auth/callback`
4. Note the **Application (client) ID**, create a **client secret**
5. API permissions → Microsoft Graph → Delegated: `User.Read`, `Files.ReadWrite.All`, `Tasks.ReadWrite`, `Calendars.ReadWrite`, `Mail.Read`, `Notes.ReadWrite`

### Run locally

```bash
cp .env.example .env
# fill in your credentials

# backend
cd backend
python -m venv venv && source venv/bin/activate
pip install -r ../requirements.txt
uvicorn main:app --reload

# frontend (separate terminal)
cd frontend
npm install
npm run dev
```

Open http://localhost:5173

### Docker

```bash
# dev (hot reload)
docker-compose up --build

# production
docker build -t project-assistant .
docker run -p 8080:8080 --env-file .env project-assistant
```

### Makefile

```bash
make dev        # backend + frontend
make test       # pytest
make lint       # ruff
make format     # ruff format
make check      # lint + type check + tests
```

## Environment variables

Copy `.env.example` and fill in:

**Required:**
- `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET`, `AZURE_TENANT_ID` (use `common` for personal accounts)
- `SECRET_KEY` — session encryption
- At least one of: `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `GOOGLE_API_KEY`

**Optional:**
- `GITHUB_TOKEN`, `GITHUB_USERNAME` — for GitHub integration
- `TELEGRAM_API_ID`, `TELEGRAM_API_HASH`, `TELEGRAM_PHONE` — for Telegram
- `ARXIV_CATEGORIES`, `ARXIV_INTERESTS` — for paper digest
- `ONEDRIVE_BASE_FOLDER` (default: `PersonalAI`)
- `DEFAULT_LLM_PROVIDER` (default: `anthropic`)

See `.env.example` for the full list.

## Project structure

```
backend/
├── main.py           # FastAPI app
├── auth.py           # OAuth, multi-account
├── config.py         # Settings
├── routers/          # chat, notes, tasks, calendar, email, github, telegram, arxiv, actions, sync
└── services/         # graph client, ai, vectors, sync, actions

frontend/src/
├── App.jsx
└── components/       # Chat, Notes, NoteEditor, Tasks, Calendar, Email, Actions

tests/
├── conftest.py       # Fixtures, mock graph client
└── test_notes.py     # Notes endpoint tests
```

## OneDrive folder structure

The app uses this layout in your OneDrive:

```
PersonalAI/
├── Diary/
├── Projects/
│   └── SubFolder/    # nested folders supported
├── Study/
└── Inbox/
```

Folders can be created and managed from the UI at any level.

## Troubleshooting

**"unauthorized_client" on sign-in with personal Microsoft account:**
Azure Portal → App registrations → your app → Manifest → change `signInAudience` to `AzureADandPersonalMicrosoftAccount` → Save. The UI won't let you change this for existing registrations, use the Manifest editor.

**"AADSTS900144: request body must contain client_id":**
Check `.env` exists and `AZURE_CLIENT_ID` / `AZURE_CLIENT_SECRET` are set. Restart backend after changes.

**Sign-in redirect loops:**
Verify redirect URI in Azure matches exactly: `http://localhost:8000/auth/callback`

## License

Proprietary. See [LICENSE](LICENSE) for terms. No use, copying, or modification without written permission.
