# Web Search & URL Fetching

The assistant can search the web and fetch webpage content for current information.

## Web Search

When enabled (`ENABLE_WEB_SEARCH=true`), the AI can search the web.

### How It Works

1. AI determines it needs current information
2. Outputs a `SEARCH` block with the query
3. System executes search via DuckDuckGo
4. Results are added to context
5. AI re-generates response with search results

### Example

```
User: What's the current price of Bitcoin?
AI: [Performs web search]
Based on my search, Bitcoin is currently trading at...
```

### Limitations

- Maximum 3 searches per request
- 10 second timeout per search
- Results are summarized, not full pages

## URL Fetching

When enabled (`ENABLE_URL_FETCH=true`), the AI can read webpage content.

### How It Works

1. User provides a URL or AI needs to read a page
2. AI outputs a `FETCH` block with the URL
3. System fetches and extracts text content
4. Content is added to context
5. AI re-generates response with page content

### Example

```
User: Summarize this article: https://example.com/news/article
AI: [Fetches page content]
The article discusses...
```

### Limitations

- Maximum 3 URLs per request
- 15 second timeout per fetch
- Content truncated to ~50,000 characters
- Only public HTTP/HTTPS URLs
- HTML text extraction (no JavaScript rendering)

## Security

### Blocked Domains

For security, these domains are blocked:
- localhost
- 127.0.0.1
- internal/intranet domains

### Content Sanitization

All fetched content is:
- Sanitized for prompt injection attempts
- Length-limited to prevent context overflow
- HTML-escaped to prevent format issues

## Configuration

```bash
ENABLE_WEB_SEARCH=true
ENABLE_URL_FETCH=true
```

In `prompt_config.yaml`:

```yaml
roles:
  general:
    enable_search: true
    enable_fetch: true
```
