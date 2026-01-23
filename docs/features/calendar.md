# Calendar

The Calendar feature integrates with Outlook Calendar for event management.

## Features

- View upcoming events
- Create new events
- Check availability
- Get daily/weekly summaries

## AI Integration

The AI can help with scheduling:

```
User: Schedule a meeting with John tomorrow at 2pm
AI: I'll create that event...
[Proposes CREATE_EVENT action with details]
```

## API Endpoints

### Get Calendar View

```http
GET /calendar/view?start={datetime}&end={datetime}
```

### Today's Events

```http
GET /calendar/today
```

### This Week

```http
GET /calendar/week
```

### Create Event

```http
POST /calendar/create
{
  "subject": "Meeting with John",
  "start_datetime": "2024-03-15T14:00:00",
  "end_datetime": "2024-03-15T15:00:00",
  "body": "Discuss project timeline"
}
```

## Context in Chat

Calendar events are included in chat context, enabling:

- Awareness of your schedule
- Conflict detection
- Time-based suggestions

## Required Permissions

Requires `Calendars.ReadWrite` scope in Azure AD.
