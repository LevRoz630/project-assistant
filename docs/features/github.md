# GitHub

The GitHub feature integrates with your GitHub account for issue and PR management.

## Setup

1. Create a Personal Access Token at https://github.com/settings/tokens
2. Required scopes: `repo`, `notifications`, `read:user`
3. Add to `.env`:

```bash
GITHUB_TOKEN=ghp_your-token-here
GITHUB_USERNAME=your-username
```

## Features

- List repositories
- View and create issues
- View and create pull requests
- Manage comments and reviews
- Get notifications

## API Endpoints

### Repositories

```http
GET /github/repos
GET /github/repos/{owner}/{repo}
```

### Issues

```http
GET /github/repos/{owner}/{repo}/issues
POST /github/repos/{owner}/{repo}/issues
GET /github/issues/{issue_id}
```

### Pull Requests

```http
GET /github/repos/{owner}/{repo}/pulls
GET /github/pulls/{pr_id}
```

### Notifications

```http
GET /github/notifications
```

## AI Integration

The AI is aware of your GitHub activity and can:

- Summarize open issues
- Help draft issue descriptions
- Review PR status
