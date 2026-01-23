# Email

The Email feature provides read-only access to your Outlook inbox.

## Features

- View recent emails
- Search emails
- AI-powered email summarization
- Draft suggestions (via AI)

## AI Integration

The AI can help with email:

```
User: Summarize my unread emails
AI: [Reviews email context and provides summary]

User: Draft a reply to John's email about the project
AI: [Proposes DRAFT_EMAIL action]
```

## API Endpoints

### List Inbox Messages

```http
GET /email/inbox?top=10
```

### Search Emails

```http
GET /email/search?query=project%20update
```

### List Folders

```http
GET /email/folders
```

## Context in Chat

Recent emails are included in chat context, allowing:

- Email summarization
- Response suggestions
- Priority identification

## Security Note

The application only has **read** access to emails (`Mail.Read`). It cannot send emails on your behalf without explicit action.

## Required Permissions

Requires `Mail.Read` scope in Azure AD.
