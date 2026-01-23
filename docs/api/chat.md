# Chat Endpoints

The Chat API provides AI-powered conversation capabilities.

## Send Message

```http
POST /chat/send
```

### Request

```json
{
  "message": "What meetings do I have today?",
  "history": [
    {"role": "user", "content": "Hello"},
    {"role": "assistant", "content": "Hi! How can I help?"}
  ],
  "use_context": true,
  "include_tasks": true,
  "include_calendar": true,
  "include_email": true
}
```

### Response

```json
{
  "response": "You have 3 meetings today...",
  "context_used": true,
  "sources": ["Projects/meeting-notes.md"],
  "proposed_actions": [
    {
      "id": "abc123",
      "type": "create_task",
      "data": {
        "title": "Prepare for client meeting",
        "due_date": "2024-03-15T09:00:00"
      }
    }
  ]
}
```

## Stream Message

```http
POST /chat/stream
```

Same request body as `/chat/send`.

### Response (Server-Sent Events)

```
data: {"type": "meta", "sources": ["file.md"]}

data: {"type": "content", "content": "You have"}

data: {"type": "content", "content": " 3 meetings"}

data: {"type": "done"}
```

## Vector Store Stats

```http
GET /chat/stats
```

### Response

```json
{
  "total_documents": 150,
  "total_chunks": 450,
  "collection_name": "personal_notes"
}
```

## Ingest Notes

Re-index all notes into the vector store.

```http
POST /chat/ingest
```

### Response

```json
{
  "ingested": 45,
  "errors": null
}
```

## Conversation History

### Get History

```http
GET /chat/history
```

### Save History

```http
POST /chat/history
{
  "conversations": [
    {
      "id": "conv-123",
      "title": "Meeting planning",
      "messages": [...]
    }
  ]
}
```

### Delete Conversation

```http
DELETE /chat/history/{conversation_id}
```

## Input Validation

- **message**: Required, max 10,000 characters
- Empty messages are rejected
- Whitespace-only messages are rejected

## Security Features

- User messages are checked for prompt injection patterns
- Security events are logged but messages are still processed
- Search queries are sanitized
- Fetched URLs are validated and content sanitized

## Rate Limiting

Chat endpoints are limited to 60 requests per minute per session.

Response when exceeded:
```json
{
  "detail": "Too many requests. Please wait before trying again."
}
```
