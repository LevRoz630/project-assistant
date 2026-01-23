# Authentication

The API uses Microsoft OAuth 2.0 for authentication with session-based authorization.

## OAuth Flow

### 1. Initiate Login

```http
GET /auth/login
```

Redirects to Microsoft login page.

### 2. Handle Callback

After successful Microsoft login, the user is redirected to:

```
/auth/callback?code=...&state=...
```

The backend:
1. Exchanges the code for tokens
2. Creates a session
3. Sets a `session_id` cookie
4. Redirects to the frontend

### 3. Authenticated Requests

All subsequent requests include the session cookie automatically.

## Session Management

### Check Status

```http
GET /auth/status
```

Response:
```json
{
  "authenticated": true,
  "user": {
    "name": "John Doe",
    "email": "john@example.com"
  }
}
```

### Logout

```http
POST /auth/logout
```

Clears the session and removes the cookie.

## Multi-Account Support

The system supports multiple Microsoft accounts with different purposes:

- **PRIMARY**: All services
- **EMAIL**: Email & Calendar only
- **STORAGE**: OneDrive & To Do only

### Link Additional Account

```http
GET /auth/login/{purpose}
```

Where `purpose` is `email` or `storage`.

### List Linked Accounts

```http
GET /auth/accounts
```

## Token Handling

- Tokens are cached server-side
- Automatic token refresh before expiration
- Session expires after 7 days of inactivity

## Security

- `httponly` cookies prevent XSS access
- `secure` flag in production (HTTPS only)
- `samesite=lax` for CSRF protection
- State parameter validates OAuth flow

## Error Responses

### 401 Unauthorized

```json
{
  "detail": "Not authenticated"
}
```

### 401 Session Expired

```json
{
  "detail": "Session expired"
}
```

Solution: Re-authenticate via `/auth/login`.
