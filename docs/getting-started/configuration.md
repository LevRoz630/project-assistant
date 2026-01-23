# Configuration

The application is configured through environment variables in the `.env` file.

## Quick Setup

```bash
cp .env.example .env
# Edit .env with your credentials
```

## Required Settings

### Microsoft Azure AD

```bash
AZURE_CLIENT_ID=your-azure-client-id
AZURE_CLIENT_SECRET=your-azure-client-secret
AZURE_TENANT_ID=common  # Use "common" for personal accounts
AZURE_REDIRECT_URI=http://localhost:8000/auth/callback
```

See [Azure Setup](azure-setup.md) for detailed instructions.

### AI Provider (at least one required)

```bash
ANTHROPIC_API_KEY=your-anthropic-api-key
OPENAI_API_KEY=your-openai-api-key
GOOGLE_API_KEY=your-google-api-key
```

Get API keys from:
- Anthropic: https://console.anthropic.com/
- OpenAI: https://platform.openai.com/api-keys
- Google: https://makersuite.google.com/app/apikey

### LLM Settings

```bash
# Provider: anthropic, openai, or google
DEFAULT_LLM_PROVIDER=anthropic

# Model name (depends on provider)
DEFAULT_MODEL=claude-sonnet-4-20250514
```

Available models by provider:
- **Anthropic**: `claude-sonnet-4-20250514`, `claude-3-haiku-20240307`, `claude-3-opus-20240229`
- **OpenAI**: `gpt-4`, `gpt-4-turbo`, `gpt-3.5-turbo`
- **Google**: `gemini-1.5-pro`, `gemini-1.5-flash`

## Application Settings

```bash
DEBUG=true
SECRET_KEY=your-secret-key-change-in-production
```

For production, generate a secure secret key:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

## Storage Settings

### OneDrive

```bash
ONEDRIVE_BASE_FOLDER=PersonalAI  # Folder for storing notes
```

### Vector Store

```bash
CHROMA_PERSIST_DIRECTORY=./data/chroma
```

## Integration Settings

### GitHub

```bash
GITHUB_TOKEN=ghp_your-token-here
GITHUB_USERNAME=your-username
```

Get a fine-grained token from https://github.com/settings/tokens?type=beta

Required permissions:
- Issues: Read and write
- Pull requests: Read and write
- Contents: Read-only
- Metadata: Read-only

### Telegram (optional)

```bash
TELEGRAM_API_ID=your-api-id
TELEGRAM_API_HASH=your-api-hash
TELEGRAM_PHONE=+1234567890
TELEGRAM_SESSION_PATH=./data/telegram_session
```

Get credentials from https://my.telegram.org

### ArXiv Digest

```bash
# arXiv category codes (comma-separated)
ARXIV_CATEGORIES=cs.AI,cs.CL,cs.LG,q-fin.ST,stat.ML

# Research interests for relevance ranking
ARXIV_INTERESTS=AI agents, LLMs, NLP, quantitative finance, ML for trading

# UTC hour for daily digest (0-23)
ARXIV_SCHEDULE_HOUR=6

# Papers to fetch and include
ARXIV_MAX_PAPERS=50
ARXIV_TOP_N=10

# LLM provider for ranking (uses fast models)
ARXIV_LLM_PROVIDER=anthropic
```

See https://arxiv.org/category_taxonomy for category codes.

## Web Features

```bash
ENABLE_WEB_SEARCH=true
ENABLE_URL_FETCH=true
```

## Frontend

```bash
FRONTEND_URL=http://localhost:5173
```

For production, set this to your deployed frontend URL.

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

## Production Configuration

For production deployments:

1. Set `DEBUG=false`
2. Generate a secure `SECRET_KEY`
3. Update `FRONTEND_URL` to your domain
4. Update `AZURE_REDIRECT_URI` to your callback URL
5. Configure HTTPS (handled by Fly.io or your reverse proxy)

### Fly.io Environment

Set secrets via CLI:

```bash
flyctl secrets set \
  AZURE_CLIENT_ID=... \
  AZURE_CLIENT_SECRET=... \
  ANTHROPIC_API_KEY=... \
  SECRET_KEY=...
```

Non-secret environment variables go in `fly.toml`:

```toml
[env]
  DEBUG = "false"
  FRONTEND_URL = "https://your-app.fly.dev"
```
