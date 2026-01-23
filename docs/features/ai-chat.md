# AI Chat

The AI Chat is the core feature of the Personal AI Assistant, providing intelligent conversations enhanced with your personal data.

## How It Works

1. **Message Input** - You send a message to the assistant
2. **Role Detection** - The system detects the appropriate AI role (email, tasks, calendar, etc.)
3. **Context Gathering** - Relevant context is gathered from your data:
   - Notes (via semantic search)
   - Tasks from Microsoft To Do
   - Calendar events from Outlook
   - Recent emails
4. **LLM Generation** - The AI generates a response using the gathered context
5. **Action Parsing** - Any proposed actions are extracted for your approval

## Supported Roles

The AI automatically switches roles based on your message:

| Role | Keywords | Capabilities |
|------|----------|--------------|
| **General** | (default) | Full assistant with all features |
| **Email** | email, mail, inbox, reply | Email management and drafting |
| **Tasks** | task, todo, reminder | Task management and prioritization |
| **Calendar** | calendar, meeting, schedule | Event scheduling and availability |
| **Notes** | note, diary, journal | Note creation and retrieval |
| **Research** | search, find out, look up | Web search and URL fetching |

## Proposed Actions

The AI can propose actions for your approval:

- **Create Event** - Add to your Outlook calendar
- **Create Task** - Add to Microsoft To Do
- **Create Note** - Save to OneDrive
- **Draft Email** - Prepare email drafts

Actions are shown as proposals - you must approve them before they execute.

## Web Search

When enabled, the AI can search the web for current information:

```
User: What's the latest news about AI?
AI: Let me search for that...
[AI performs web search and includes results in response]
```

## URL Fetching

The AI can read and analyze webpage content:

```
User: Summarize this article: https://example.com/article
AI: [Fetches and summarizes the page content]
```

## Streaming

The `/chat/stream` endpoint provides real-time streaming responses for better user experience.

## Configuration

Customize AI behavior in `prompt_config.yaml`:

```yaml
roles:
  general:
    custom_instructions: "Be concise"
    enable_actions: true
    enable_search: true
    enable_fetch: true
```
