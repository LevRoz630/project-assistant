# Configuration

The application is configured through environment variables in the `.env` file.

## Required Settings

### Microsoft Azure AD

```bash
AZURE_CLIENT_ID=your-azure-client-id
AZURE_CLIENT_SECRET=your-azure-client-secret
AZURE_TENANT_ID=common  # Use "common" for personal accounts
AZURE_REDIRECT_URI=http://localhost:8000/auth/callback
```

### AI Provider (at least one required)

```bash
ANTHROPIC_API_KEY=your-anthropic-api-key
OPENAI_API_KEY=your-openai-api-key
GOOGLE_API_KEY=your-google-api-key
```

### LLM Settings

```bash
DEFAULT_LLM_PROVIDER=anthropic  # Options: anthropic, openai, google
DEFAULT_MODEL=claude-sonnet-4-20250514
```

## Optional Settings

### Application

```bash
DEBUG=true
SECRET_KEY=your-secret-key-change-in-production
```

### OneDrive

```bash
ONEDRIVE_BASE_FOLDER=PersonalAI  # Folder for storing notes
```

### Vector Store

```bash
CHROMA_PERSIST_DIRECTORY=./data/chroma
```

### Telegram

```bash
TELEGRAM_API_ID=your-api-id
TELEGRAM_API_HASH=your-api-hash
TELEGRAM_PHONE=+1234567890
TELEGRAM_SESSION_PATH=./data/telegram_session
```

### GitHub

```bash
GITHUB_TOKEN=ghp_your-token-here
GITHUB_USERNAME=your-username
```

### Web Features

```bash
ENABLE_WEB_SEARCH=true
ENABLE_URL_FETCH=true
```

### Frontend

```bash
FRONTEND_URL=http://localhost:5173
```

## Prompt Configuration

For customizing AI behavior per role, edit `backend/prompt_config.yaml`:

```yaml
global_instructions: "Additional instructions for all roles"

roles:
  general:
    custom_instructions: "Be concise and helpful"
    enable_actions: true
    enable_search: true
    enable_fetch: true

  email:
    custom_instructions: "Always be formal in email drafts"
```

Changes take effect immediately without restart.
