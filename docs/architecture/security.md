# Security

The Personal AI Assistant implements multiple layers of security.

## Prompt Injection Defense

### Detection Patterns

The `PromptSanitizer` class detects potential prompt injection attempts:

**Instruction Override Patterns**
- "ignore previous instructions"
- "forget all previous"
- "you are now a..."
- "new instructions/rules"
- "override instructions"

**Role Switching**
- "```system" in code blocks
- "[INST]" markers
- "human:/assistant:/system:" labels

**Identity Manipulation**
- "as an AI"
- "pretend to be"
- "you must now/always/never"

### Unicode Normalization

Prevents obfuscation attacks using lookalike characters:

```python
# "ｉｇｎｏｒｅ" (fullwidth) → "ignore" (ASCII)
unicodedata.normalize("NFKC", text)
```

### Content Sanitization

All external data is sanitized before LLM injection:

- **Length Truncation**: Prevents context overflow
- **HTML Escaping**: Prevents format breaking
- **Whitespace Normalization**: Prevents obfuscation
- **Pattern Detection**: Filters dangerous content

### Per-Content-Type Limits

| Content Type | Max Length |
|--------------|------------|
| Email sender | 100 chars |
| Email subject | 200 chars |
| Email preview | 300 chars |
| Task title | 200 chars |
| Task body | 500 chars |
| Calendar subject | 200 chars |
| Note content | 1000 chars |

## Input Validation

### Message Validation

- Maximum 10,000 characters
- Empty messages rejected
- Whitespace-only rejected

### URL Validation

- Only HTTP/HTTPS allowed
- Blocked domains: localhost, 127.0.0.1, internal

## Rate Limiting

### Implementation

Simple in-memory rate limiter on chat endpoints:

- **Limit**: 60 requests per minute
- **Scope**: Per session
- **Response**: 429 Too Many Requests

### Production Recommendation

Use Redis for distributed rate limiting:

```python
# Replace in-memory dict with Redis
import redis
r = redis.Redis()
```

## Security Event Logging

All security events are logged:

```python
log_security_event(
    SecurityEventType.INJECTION_ATTEMPT,
    session_id,
    {"source": "user_message", "message_length": 500}
)
```

### Event Types

- `injection_attempt` - Potential prompt injection
- `rate_limit_exceeded` - Too many requests
- `suspicious_pattern` - Other suspicious activity

## Authentication Security

### Session Cookies

- `httponly=True` - No JavaScript access
- `secure=True` (production) - HTTPS only
- `samesite=lax` - CSRF protection
- 7-day expiration

### OAuth State

State parameter validates OAuth flow integrity.

### Token Storage

- Tokens stored server-side only
- Never exposed to frontend
- Automatic refresh before expiration

## CORS Configuration

```python
allow_origins=[
    "http://localhost:5173",
    "http://localhost:3000",
]
allow_credentials=True
```

## Best Practices

### Production Checklist

1. Change `SECRET_KEY` to a strong random value
2. Set `DEBUG=false`
3. Use HTTPS
4. Configure proper CORS origins
5. Implement persistent rate limiting (Redis)
6. Enable security monitoring/alerting
7. Regular dependency updates

### Sensitive Data

- API keys in environment variables only
- Never commit `.env` files
- Use Azure Key Vault or similar for production
