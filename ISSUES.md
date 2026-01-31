# Project Assistant - Code Audit Issues

Comprehensive list of issues identified during code review.

---

## Critical Issues

### 1. XSS Vulnerability in Email Component
- **File:** `frontend/src/components/Email.jsx`
- **Lines:** 204-211
- **Description:** Email body content rendered via `dangerouslySetInnerHTML` without sanitization
- **Risk:** Malicious emails can execute arbitrary JavaScript in user's browser
- **Fix:** Add DOMPurify sanitization before rendering HTML content

### 2. Path Traversal in Notes Router
- **File:** `backend/routers/notes.py`
- **Lines:** 110-117, 234-239, 272-276
- **Description:** Filename and folder parameters not validated for path traversal attacks
- **Risk:** Attacker can access files outside intended directory via `../` sequences
- **Fix:** Validate and reject paths containing `..` or starting with `/`

### 3. Hardcoded Default Secret Key
- **File:** `backend/config.py`
- **Line:** 14
- **Description:** `SECRET_KEY` defaults to `"change-me-in-production"`
- **Risk:** Session forgery if deployed without setting proper secret
- **Fix:** Remove default, require explicit configuration

### 4. SSRF in Web Fetch Service
- **File:** `backend/services/web_fetch.py`
- **Lines:** 35-56
- **Description:** URL validation insufficient - hostname check uses `in` operator, no private IP blocking
- **Risk:** Server-side request forgery to internal services
- **Fix:** Use proper URL parsing, block private IP ranges (10.x, 172.16.x, 192.168.x, 127.x)

---

## High Priority Issues

### 5. Rate Limiter Memory Leak
- **File:** `backend/main.py`
- **Lines:** 32-100
- **Description:** `_request_counts` dict never cleaned of empty/expired entries
- **Risk:** Memory exhaustion with random session IDs
- **Fix:** Delete entries when empty, or use Redis-based rate limiting

### 6. Unbounded Chat History Array
- **File:** `backend/routers/chat.py`
- **Lines:** 280, 400-401, 616-617
- **Description:** No validation on chat history array size
- **Risk:** Memory exhaustion, DoS via massive history payloads
- **Fix:** Add `MAX_HISTORY_SIZE` validation

### 7. Token Expiry Not Validated
- **File:** `backend/auth.py`
- **Lines:** 152-155
- **Description:** Access tokens returned without checking expiry timestamp
- **Risk:** Expired tokens cause silent failures, wasted API calls
- **Fix:** Check `expires_on` before returning token, refresh if needed

### 8. OAuth State Not Bound to Session
- **File:** `backend/auth.py`
- **Lines:** 68, 193-194
- **Description:** State tokens stored globally, not tied to requesting session
- **Risk:** Potential cross-user state collision in multi-user environment
- **Fix:** Bind state to session ID, validate on callback

### 9. Verbose Exception Messages Leak Internals
- **Files:** Multiple routers
- **Examples:** `chat.py:426`, `actions.py:234`, `notes.py:231`, `tasks.py:210`
- **Description:** `f"Failed: {str(e)}"` exposes internal error details
- **Risk:** Information disclosure to attackers
- **Fix:** Return generic error messages, log details server-side

### 10. Missing Pagination Bounds
- **File:** `backend/routers/email.py`
- **Lines:** 23-28, 67-72, 150-155
- **Description:** `top` and `skip` query params have no max/min validation
- **Risk:** Resource exhaustion with `?top=999999`
- **Fix:** Add Query validators with bounds (e.g., `Query(le=100, ge=0)`)

---

## Medium Priority Issues

### 11. Global Mutable State (Thread Safety)
- **File:** `backend/auth.py`
- **Lines:** 18, 67-68
- **Description:** `_token_cache` and `_state_cache` are global dicts modified without locks
- **Risk:** Race conditions in multi-worker deployment
- **Fix:** Add `threading.Lock` or use Redis exclusively

### 12. N+1 Query Pattern in Sync
- **File:** `backend/services/sync.py`
- **Lines:** 99-141
- **Description:** Individual API call per folder and per file during sync
- **Risk:** Slow sync, API rate limiting
- **Fix:** Batch operations or implement proper delta sync

### 13. Delta Sync Falls Back to Full Sync
- **File:** `backend/services/sync.py`
- **Lines:** 156-162
- **Description:** `_delta_sync()` always calls `_full_sync()` instead
- **Risk:** Unnecessary data transfer and processing
- **Fix:** Implement Microsoft Graph delta API properly

### 14. Overly Broad Exception Handling
- **Files:** `backend/services/vectors.py:127,143`, `backend/routers/notes.py:359-368`, `backend/services/github.py:40`
- **Description:** `contextlib.suppress(Exception)` and bare `except Exception:` hide errors
- **Risk:** Debugging impossible, security issues masked
- **Fix:** Catch specific exception types

### 15. Silent Failures with Pass Statements
- **File:** `backend/routers/chat.py`
- **Lines:** 47, 772
- **Description:** JSON decode errors and folder creation failures silently ignored
- **Risk:** Data corruption goes unnoticed
- **Fix:** Log errors, handle gracefully with user feedback

### 16. Stream Response Missing Error Handling
- **File:** `backend/routers/chat.py`
- **Lines:** 622-650
- **Description:** If streaming generator throws, client never receives 'done' message
- **Risk:** Client hangs waiting for stream completion
- **Fix:** Wrap generator in try/finally to ensure 'done' sent

### 17. Action Data Not Schema Validated
- **File:** `backend/routers/actions.py`
- **Lines:** 91-96
- **Description:** `data: dict` accepts arbitrary structure, execution assumes specific keys
- **Risk:** Runtime errors on malformed action data
- **Fix:** Create per-action-type Pydantic models

### 18. YAML Injection in Note Metadata
- **File:** `backend/routers/notes.py`
- **Lines:** 150-156
- **Description:** User input inserted into YAML frontmatter via f-string
- **Risk:** YAML structure corruption or injection
- **Fix:** Use `yaml.dump()` for safe serialization

### 19. Action Store Never Cleaned
- **File:** `backend/services/actions.py`
- **Lines:** 152-162
- **Description:** `clear_old()` method exists but is never called
- **Risk:** Memory grows indefinitely with old actions
- **Fix:** Add periodic cleanup via background task

### 20. Missing React Error Boundaries
- **Files:** All frontend components
- **Description:** No error boundary wrapping components
- **Risk:** Any component crash takes down entire app
- **Fix:** Add root-level ErrorBoundary component

### 21. Memory Leak in ArxivDigest Polling
- **File:** `frontend/src/components/ArxivDigest.jsx`
- **Lines:** 94-111
- **Description:** `setInterval` not stored as ref, not cleared on unmount
- **Risk:** Interval continues after unmount, state updates on unmounted component
- **Fix:** Store interval in `useRef`, clear in cleanup function

### 22. Inline Style Objects Cause Re-renders
- **Files:** Multiple frontend components
- **Description:** Inline style objects recreated every render
- **Risk:** Unnecessary re-renders, performance degradation
- **Fix:** Move styles to CSS or use `useMemo`

### 23. Context Fetching Code Duplicated
- **File:** `backend/routers/chat.py`
- **Lines:** 328-388 and 544-603
- **Description:** Identical async functions defined in both `send_message` and `stream_message`
- **Risk:** Bug fixes need applying twice, maintenance burden
- **Fix:** Extract to shared module-level functions

### 24. Auth Check Pattern Duplicated
- **Files:** All backend routers
- **Description:** Same session/token validation code repeated in every endpoint
- **Risk:** Inconsistent handling, maintenance burden
- **Fix:** Create `Depends(get_authenticated_session)` dependency

### 25. GitHub Query String Injection
- **File:** `backend/services/github.py`
- **Lines:** 216, 238
- **Description:** User input inserted into GitHub search queries via f-strings
- **Risk:** Query manipulation via special characters
- **Fix:** Validate/escape input or use parameterized queries

### 26. Action History Sync Race Condition
- **File:** `backend/routers/actions.py`
- **Lines:** 50-69, 71-88, 125-133
- **Description:** Cloud file read/write without locking
- **Risk:** Lost updates when multiple instances sync simultaneously
- **Fix:** Add optimistic locking or use atomic operations

---

## Low Priority Issues

### 27. Hardcoded Rate Limit Values
- **File:** `backend/main.py`
- **Lines:** 33-34
- **Description:** `RATE_LIMIT_REQUESTS = 60` and window hardcoded
- **Fix:** Move to `config.py` as environment variables

### 28. Hardcoded Excluded Folders
- **File:** `backend/routers/notes.py`
- **Lines:** 60, 76, 354
- **Description:** `{".obsidian", ".trash", "_system"}` hardcoded
- **Fix:** Move to configuration

### 29. Hardcoded Context Limits
- **File:** `backend/routers/chat.py`
- **Lines:** 158, 167, 208, 248
- **Description:** Limits like `lists[:5]`, `tasks[:10]`, `events[:15]` hardcoded
- **Fix:** Move to configuration for tuning

### 30. Hardcoded Timeout Values
- **Files:** `web_fetch.py:15`, `search.py:16`, `chat.py:334,419`
- **Description:** Various timeout values hardcoded
- **Fix:** Move to configuration

### 31. Regex Compiled on Every Request
- **File:** `backend/routers/chat.py`
- **Lines:** 38, 56, 88
- **Description:** `re.findall(pattern, ...)` recompiles pattern each call
- **Fix:** Use `re.compile()` at module level

### 32. Using Array Index as React Keys
- **File:** `frontend/src/components/Chat.jsx`
- **Lines:** 481, 493
- **Description:** `key={idx}` used instead of unique IDs
- **Risk:** Incorrect reconciliation on list reorder
- **Fix:** Use message IDs or generate stable keys

### 33. Browser alert/confirm Usage
- **Files:** `NoteEditor.jsx:63,70,85`, `Tasks.jsx:153`, `Actions.jsx:52,73`, `Chat.jsx:410`, `Accounts.jsx:13`, `Calendar.jsx:99`
- **Description:** Native dialogs block UI and break UX flow
- **Fix:** Replace with custom modal components

### 34. Missing ARIA Labels
- **Files:** Multiple frontend forms
- **Description:** Form inputs lack proper accessibility labels
- **Fix:** Add `aria-label` or associated `<label>` elements

### 35. Hardcoded Default Folders in Notes
- **File:** `frontend/src/components/Notes.jsx`
- **Lines:** 8, 34, 38, 127, 142
- **Description:** `['Diary', 'Projects', 'Study', 'Inbox']` repeated 4 times
- **Fix:** Extract to constant

### 36. Sequential Folder Creation
- **File:** `backend/routers/notes.py`
- **Lines:** 364-369
- **Description:** Folders created one-by-one with sequential awaits
- **Fix:** Use `asyncio.gather()` for parallel creation

### 37. Telegram API ID Type Issue
- **File:** `backend/config.py`
- **Lines:** 47-48
- **Description:** `telegram_api_id: int = 0` - zero is technically valid but nonsensical
- **Fix:** Use `Optional[int] = None` and validate before use

### 38. Unused Return Values
- **File:** `backend/services/security.py`
- **Lines:** 31-57
- **Description:** `log_security_event()` returns data that's never used
- **Fix:** Remove return or use for correlation

### 39. Missing Input Length Validation
- **Files:** Various frontend forms
- **Description:** No max length checks on text inputs before API calls
- **Fix:** Add maxLength to inputs, validate before submit

### 40. Modal Focus Not Trapped
- **Files:** `Notes.jsx`, `Tasks.jsx`, `Calendar.jsx`
- **Description:** Modal dialogs don't trap focus or handle ESC key
- **Fix:** Add keyboard event handling and focus management

---

## Summary by Category

| Category | Critical | High | Medium | Low | Total |
|----------|----------|------|--------|-----|-------|
| Security | 4 | 3 | 3 | 0 | 10 |
| Error Handling | 0 | 1 | 4 | 0 | 5 |
| Performance | 0 | 1 | 3 | 2 | 6 |
| Memory/Resources | 0 | 2 | 2 | 0 | 4 |
| Input Validation | 0 | 2 | 1 | 1 | 4 |
| Code Quality | 0 | 0 | 2 | 6 | 8 |
| Configuration | 0 | 0 | 0 | 5 | 5 |
| React/Frontend | 0 | 0 | 3 | 5 | 8 |
| **Total** | **4** | **9** | **18** | **19** | **50** |

---

## Recommended Fix Order

1. **Critical Security** - XSS, path traversal, secret key, SSRF
2. **High Security** - Rate limiter, token handling, OAuth state
3. **High Stability** - Chat history limits, error messages, pagination
4. **Medium Security** - Thread safety, query injection, race conditions
5. **Medium Stability** - Error handling, stream fixes, validation
6. **Frontend Issues** - Error boundaries, memory leaks, accessibility
7. **Code Quality** - Duplication, configuration, performance
