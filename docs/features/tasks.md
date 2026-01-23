# Tasks

The Tasks feature integrates with Microsoft To Do for task management.

## Features

- View task lists and tasks
- Create new tasks
- Mark tasks as complete
- Set due dates and priorities

## AI Integration

The AI can help with task management:

```
User: Add a task to review the budget report by Friday
AI: I'll create that task for you...
[Proposes CREATE_TASK action]
```

## API Endpoints

### List Task Lists

```http
GET /tasks/lists
```

### Get Tasks in a List

```http
GET /tasks/lists/{list_id}/tasks
```

### Create Task

```http
POST /tasks/lists/{list_id}/tasks
{
  "title": "Review budget report",
  "body": "Need to analyze Q4 numbers",
  "due_date": "2024-03-15T17:00:00"
}
```

### Complete Task

```http
POST /tasks/{task_id}/complete
```

## Context in Chat

Tasks are automatically included in chat context, allowing the AI to:

- Remind you of upcoming deadlines
- Help prioritize your work
- Suggest task organization

## Required Permissions

Requires `Tasks.ReadWrite` scope in Azure AD.
