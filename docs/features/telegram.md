# Telegram

The Telegram feature provides access to your Telegram messages.

## Setup

1. Get API credentials from https://my.telegram.org
2. Add to `.env`:

```bash
TELEGRAM_API_ID=your-api-id
TELEGRAM_API_HASH=your-api-hash
TELEGRAM_PHONE=+1234567890
TELEGRAM_SESSION_PATH=./data/telegram_session
```

3. Authenticate via the `/telegram/auth` endpoint

## Features

- List dialogs (chats)
- Read messages
- Message summaries

## API Endpoints

### List Dialogs

```http
GET /telegram/dialogs
```

### Get Messages

```http
GET /telegram/messages/{dialog_id}?limit=50
```

### Authentication Status

```http
GET /telegram/status
```

### Authenticate

```http
POST /telegram/auth
{
  "phone": "+1234567890"
}

POST /telegram/auth/code
{
  "code": "12345"
}
```

## Session Management

The Telegram session is persisted to disk, so you only need to authenticate once per device.

## Security Note

Telegram credentials are sensitive. Keep your API hash secret and never share session files.
