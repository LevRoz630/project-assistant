# API Overview

The Personal AI Assistant provides a REST API built with FastAPI.

## Base URL

```
http://localhost:8000
```

## Authentication

All endpoints (except `/auth/*` and `/health`) require authentication via session cookie.

1. Initiate login: `GET /auth/login`
2. Complete OAuth flow
3. Session cookie is set automatically

## Response Format

All responses are JSON:

```json
{
  "data": { ... },
  "error": null
}
```

Error responses:

```json
{
  "detail": "Error message"
}
```

## Rate Limiting

Chat endpoints are rate-limited to **60 requests per minute** per session.

## Endpoints

### Health & Status

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | API info |
| `/health` | GET | Health check |

### Authentication

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/auth/login` | GET | Initiate OAuth |
| `/auth/callback` | GET | OAuth callback |
| `/auth/logout` | POST | End session |
| `/auth/status` | GET | Check auth status |

### Chat

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/chat/send` | POST | Send message |
| `/chat/stream` | POST | Stream response |
| `/chat/stats` | GET | Vector store stats |
| `/chat/ingest` | POST | Re-index notes |
| `/chat/history` | GET/POST | Conversation history |

### Notes

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/notes/list` | GET | List notes |
| `/notes/create` | POST | Create note |
| `/notes/{path}` | GET/PUT/DELETE | CRUD operations |

### Tasks

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/tasks/lists` | GET | List task lists |
| `/tasks/lists/{id}/tasks` | GET/POST | Tasks in list |
| `/tasks/{id}/complete` | POST | Complete task |

### Calendar

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/calendar/view` | GET | Calendar view |
| `/calendar/today` | GET | Today's events |
| `/calendar/week` | GET | This week |
| `/calendar/create` | POST | Create event |

### Email

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/email/inbox` | GET | Inbox messages |
| `/email/search` | GET | Search emails |
| `/email/folders` | GET | List folders |

### GitHub

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/github/repos` | GET | List repos |
| `/github/issues/*` | GET/POST | Issues |
| `/github/pulls/*` | GET | Pull requests |

### Telegram

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/telegram/dialogs` | GET | List chats |
| `/telegram/messages/{id}` | GET | Get messages |
| `/telegram/auth` | POST | Authenticate |

### Actions

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/actions/pending` | GET | Pending actions |
| `/actions/{id}/approve` | POST | Approve action |
| `/actions/{id}/reject` | POST | Reject action |

## OpenAPI Documentation

Interactive documentation available at:

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
