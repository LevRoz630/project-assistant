# Notes

The Notes feature provides AI-powered note management with semantic search capabilities.

## Storage

Notes are stored in your OneDrive under the `PersonalAI` folder (configurable via `ONEDRIVE_BASE_FOLDER`).

## Organization

Notes are organized in folders:
- **Diary** - Daily journal entries
- **Projects** - Project-related notes
- **Study** - Learning materials
- **Inbox** - Quick captures

## Creating Notes

### Via AI Chat

Ask the AI to create a note:

```
User: Create a note about today's meeting with the marketing team
AI: I'll create a note for you...
[Proposes CREATE_NOTE action]
```

### Via API

```http
POST /notes/create
{
  "folder": "Projects",
  "filename": "marketing-meeting.md",
  "content": "# Marketing Meeting\n\nDiscussion points..."
}
```

## Semantic Search (RAG)

Notes are indexed in ChromaDB for semantic search:

1. Notes are split into chunks
2. Chunks are embedded using OpenAI embeddings
3. When you chat, relevant chunks are retrieved
4. The AI uses these chunks as context

### Re-indexing

To re-index all notes:

```http
POST /chat/ingest
```

## AI Context

When enabled (`use_context: true`), the AI automatically searches your notes for relevant information:

```
User: What did I note about the budget?
AI: [Searches notes and responds with relevant content]
```

## Markdown Support

Notes are stored as Markdown files, supporting:
- Headers
- Lists
- Code blocks
- Links
- Tables
