"""GitHub API service for fetching notifications, issues, PRs, and activity."""

from datetime import datetime, timedelta

from config import get_settings
from github import Github
from github.GithubException import GithubException

settings = get_settings()

# Global client instance
_client: Github | None = None


def get_client() -> Github:
    """Get or create the GitHub client."""
    global _client

    if _client is None:
        if not settings.github_token:
            raise ValueError("GitHub token not configured")
        _client = Github(settings.github_token)

    return _client


def is_configured() -> bool:
    """Check if GitHub is configured."""
    return bool(settings.github_token)


def _format_user(user) -> dict | None:
    """Format a GitHub user."""
    if not user:
        return None
    return {
        "login": user.login,
        "name": user.name,
        "avatar_url": user.avatar_url,
    }


def _format_repo(repo) -> dict:
    """Format a GitHub repository."""
    return {
        "id": repo.id,
        "name": repo.name,
        "full_name": repo.full_name,
        "description": repo.description,
        "url": repo.html_url,
        "private": repo.private,
        "stars": repo.stargazers_count,
        "language": repo.language,
    }


def _format_issue(issue) -> dict:
    """Format a GitHub issue."""
    return {
        "id": issue.id,
        "number": issue.number,
        "title": issue.title,
        "state": issue.state,
        "url": issue.html_url,
        "created_at": issue.created_at.isoformat() if issue.created_at else None,
        "updated_at": issue.updated_at.isoformat() if issue.updated_at else None,
        "user": _format_user(issue.user),
        "assignees": [_format_user(a) for a in issue.assignees],
        "labels": [l.name for l in issue.labels],
        "comments": issue.comments,
        "repo": issue.repository.full_name if issue.repository else None,
        "is_pull_request": issue.pull_request is not None,
    }


def _format_pr(pr) -> dict:
    """Format a GitHub pull request."""
    return {
        "id": pr.id,
        "number": pr.number,
        "title": pr.title,
        "state": pr.state,
        "url": pr.html_url,
        "created_at": pr.created_at.isoformat() if pr.created_at else None,
        "updated_at": pr.updated_at.isoformat() if pr.updated_at else None,
        "merged_at": pr.merged_at.isoformat() if pr.merged_at else None,
        "user": _format_user(pr.user),
        "assignees": [_format_user(a) for a in pr.assignees] if pr.assignees else [],
        "reviewers": [_format_user(r) for r in pr.requested_reviewers] if pr.requested_reviewers else [],
        "labels": [l.name for l in pr.labels],
        "draft": pr.draft,
        "mergeable": pr.mergeable,
        "additions": pr.additions,
        "deletions": pr.deletions,
        "changed_files": pr.changed_files,
        "repo": pr.base.repo.full_name if pr.base else None,
    }


def _format_notification(notif) -> dict:
    """Format a GitHub notification."""
    return {
        "id": notif.id,
        "reason": notif.reason,
        "unread": notif.unread,
        "updated_at": notif.updated_at.isoformat() if notif.updated_at else None,
        "subject": {
            "title": notif.subject.title,
            "type": notif.subject.type,
            "url": notif.subject.url,
        },
        "repo": {
            "name": notif.repository.name,
            "full_name": notif.repository.full_name,
        },
    }


def _format_commit(commit) -> dict:
    """Format a GitHub commit."""
    return {
        "sha": commit.sha[:7],
        "full_sha": commit.sha,
        "message": commit.commit.message.split("\n")[0],  # First line only
        "url": commit.html_url,
        "author": _format_user(commit.author) if commit.author else {
            "login": commit.commit.author.name,
            "name": commit.commit.author.name,
        },
        "date": commit.commit.author.date.isoformat() if commit.commit.author.date else None,
    }


def get_user() -> dict:
    """Get the authenticated user."""
    client = get_client()
    user = client.get_user()
    return {
        "login": user.login,
        "name": user.name,
        "email": user.email,
        "avatar_url": user.avatar_url,
        "public_repos": user.public_repos,
        "followers": user.followers,
        "following": user.following,
    }


def get_notifications(
    all_notifications: bool = False,
    participating: bool = False,
    since: datetime | None = None,
) -> list[dict]:
    """Get notifications."""
    client = get_client()

    notifications = client.get_user().get_notifications(
        all=all_notifications,
        participating=participating,
        since=since,
    )

    return [_format_notification(n) for n in notifications]


def mark_notifications_read(last_read_at: datetime | None = None) -> dict:
    """Mark all notifications as read."""
    client = get_client()
    client.get_user().mark_notifications_as_read(last_read_at or datetime.now())
    return {"status": "marked_read"}


def get_assigned_issues(state: str = "open") -> list[dict]:
    """Get issues assigned to the authenticated user."""
    client = get_client()
    user = client.get_user()

    issues = user.get_issues(filter="assigned", state=state)
    return [_format_issue(i) for i in issues]


def get_created_issues(state: str = "open") -> list[dict]:
    """Get issues created by the authenticated user."""
    client = get_client()
    user = client.get_user()

    issues = user.get_issues(filter="created", state=state)
    return [_format_issue(i) for i in issues]


def get_mentioned_issues(state: str = "open") -> list[dict]:
    """Get issues where the user is mentioned."""
    client = get_client()
    user = client.get_user()

    issues = user.get_issues(filter="mentioned", state=state)
    return [_format_issue(i) for i in issues]


def get_review_requests() -> list[dict]:
    """Get PRs where the user's review is requested."""
    client = get_client()
    user = client.get_user()

    # Search for PRs where review is requested
    query = f"is:pr is:open review-requested:{user.login}"
    results = client.search_issues(query)

    prs = []
    for item in results:
        try:
            # Get full PR details
            repo = client.get_repo(item.repository.full_name)
            pr = repo.get_pull(item.number)
            prs.append(_format_pr(pr))
        except GithubException:
            # If we can't get PR details, use issue format
            prs.append(_format_issue(item))

    return prs


def get_user_prs(state: str = "open") -> list[dict]:
    """Get PRs created by the authenticated user."""
    client = get_client()
    user = client.get_user()

    query = f"is:pr author:{user.login} state:{state}"
    results = client.search_issues(query)

    prs = []
    for item in results:
        try:
            repo = client.get_repo(item.repository.full_name)
            pr = repo.get_pull(item.number)
            prs.append(_format_pr(pr))
        except GithubException:
            prs.append(_format_issue(item))

    return prs


def get_repo_activity(repo_name: str, limit: int = 20) -> dict:
    """Get recent activity on a repository."""
    client = get_client()
    repo = client.get_repo(repo_name)

    # Get recent commits
    commits = list(repo.get_commits()[:limit])

    # Get recent issues
    issues = list(repo.get_issues(state="all", sort="updated")[:limit])

    # Get recent PRs
    prs = list(repo.get_pulls(state="all", sort="updated")[:limit])

    return {
        "repo": _format_repo(repo),
        "recent_commits": [_format_commit(c) for c in commits],
        "recent_issues": [_format_issue(i) for i in issues if not i.pull_request],
        "recent_prs": [_format_issue(i) for i in issues if i.pull_request],
    }


def get_repos(type: str = "all", sort: str = "updated", limit: int = 30) -> list[dict]:
    """Get user's repositories."""
    client = get_client()
    user = client.get_user()

    repos = user.get_repos(type=type, sort=sort)
    return [_format_repo(r) for r in list(repos)[:limit]]


def get_starred_repos(limit: int = 30) -> list[dict]:
    """Get user's starred repositories."""
    client = get_client()
    user = client.get_user()

    repos = user.get_starred()
    return [_format_repo(r) for r in list(repos)[:limit]]


def get_updates_summary(hours: int = 24) -> dict:
    """Get a summary of GitHub updates in the last N hours."""
    client = get_client()
    user = client.get_user()
    since = datetime.now() - timedelta(hours=hours)

    # Get unread notifications
    notifications = list(client.get_user().get_notifications(since=since))
    unread_notifications = [n for n in notifications if n.unread]

    # Group by type
    notification_types = {}
    for n in unread_notifications:
        t = n.subject.type
        if t not in notification_types:
            notification_types[t] = []
        notification_types[t].append(_format_notification(n))

    # Get review requests
    review_requests = get_review_requests()

    # Get assigned issues
    assigned = get_assigned_issues()

    return {
        "period_hours": hours,
        "since": since.isoformat(),
        "unread_notifications": len(unread_notifications),
        "notifications_by_type": notification_types,
        "review_requests": len(review_requests),
        "review_requests_list": review_requests[:5],  # Top 5
        "assigned_issues": len(assigned),
        "assigned_issues_list": assigned[:5],  # Top 5
    }


def search_issues(query: str, limit: int = 20) -> list[dict]:
    """Search issues and PRs."""
    client = get_client()
    results = client.search_issues(query)
    return [_format_issue(i) for i in list(results)[:limit]]


def search_repos(query: str, limit: int = 20) -> list[dict]:
    """Search repositories."""
    client = get_client()
    results = client.search_repositories(query)
    return [_format_repo(r) for r in list(results)[:limit]]


# ==================== Write Operations ====================


def create_issue(
    repo_name: str,
    title: str,
    body: str | None = None,
    labels: list[str] | None = None,
    assignees: list[str] | None = None,
) -> dict:
    """Create an issue in a repository."""
    client = get_client()
    repo = client.get_repo(repo_name)

    issue = repo.create_issue(
        title=title,
        body=body or "",
        labels=labels or [],
        assignees=assignees or [],
    )
    return _format_issue(issue)


def update_issue(
    repo_name: str,
    issue_number: int,
    title: str | None = None,
    body: str | None = None,
    state: str | None = None,
    labels: list[str] | None = None,
    assignees: list[str] | None = None,
) -> dict:
    """Update an issue."""
    client = get_client()
    repo = client.get_repo(repo_name)
    issue = repo.get_issue(issue_number)

    kwargs = {}
    if title is not None:
        kwargs["title"] = title
    if body is not None:
        kwargs["body"] = body
    if state is not None:
        kwargs["state"] = state
    if labels is not None:
        kwargs["labels"] = labels
    if assignees is not None:
        kwargs["assignees"] = assignees

    issue.edit(**kwargs)
    return _format_issue(issue)


def close_issue(repo_name: str, issue_number: int) -> dict:
    """Close an issue."""
    return update_issue(repo_name, issue_number, state="closed")


def reopen_issue(repo_name: str, issue_number: int) -> dict:
    """Reopen an issue."""
    return update_issue(repo_name, issue_number, state="open")


def add_issue_comment(repo_name: str, issue_number: int, body: str) -> dict:
    """Add a comment to an issue or PR."""
    client = get_client()
    repo = client.get_repo(repo_name)
    issue = repo.get_issue(issue_number)

    comment = issue.create_comment(body)
    return {
        "id": comment.id,
        "body": comment.body,
        "user": _format_user(comment.user),
        "created_at": comment.created_at.isoformat() if comment.created_at else None,
        "url": comment.html_url,
    }


def get_issue_comments(repo_name: str, issue_number: int) -> list[dict]:
    """Get comments on an issue."""
    client = get_client()
    repo = client.get_repo(repo_name)
    issue = repo.get_issue(issue_number)

    comments = issue.get_comments()
    return [
        {
            "id": c.id,
            "body": c.body,
            "user": _format_user(c.user),
            "created_at": c.created_at.isoformat() if c.created_at else None,
            "url": c.html_url,
        }
        for c in comments
    ]


def add_labels(repo_name: str, issue_number: int, labels: list[str]) -> dict:
    """Add labels to an issue."""
    client = get_client()
    repo = client.get_repo(repo_name)
    issue = repo.get_issue(issue_number)

    issue.add_to_labels(*labels)
    return _format_issue(issue)


def remove_labels(repo_name: str, issue_number: int, labels: list[str]) -> dict:
    """Remove labels from an issue."""
    client = get_client()
    repo = client.get_repo(repo_name)
    issue = repo.get_issue(issue_number)

    for label in labels:
        try:
            issue.remove_from_labels(label)
        except GithubException:
            pass  # Label may not exist

    return _format_issue(issue)


def assign_issue(repo_name: str, issue_number: int, assignees: list[str]) -> dict:
    """Assign users to an issue."""
    client = get_client()
    repo = client.get_repo(repo_name)
    issue = repo.get_issue(issue_number)

    issue.add_to_assignees(*assignees)
    return _format_issue(issue)


def unassign_issue(repo_name: str, issue_number: int, assignees: list[str]) -> dict:
    """Unassign users from an issue."""
    client = get_client()
    repo = client.get_repo(repo_name)
    issue = repo.get_issue(issue_number)

    for assignee in assignees:
        try:
            issue.remove_from_assignees(assignee)
        except GithubException:
            pass

    return _format_issue(issue)


# ==================== PR Operations ====================


def create_pull_request(
    repo_name: str,
    title: str,
    head: str,
    base: str,
    body: str | None = None,
    draft: bool = False,
) -> dict:
    """Create a pull request."""
    client = get_client()
    repo = client.get_repo(repo_name)

    pr = repo.create_pull(
        title=title,
        body=body or "",
        head=head,
        base=base,
        draft=draft,
    )
    return _format_pr(pr)


def merge_pull_request(
    repo_name: str,
    pr_number: int,
    commit_title: str | None = None,
    commit_message: str | None = None,
    merge_method: str = "merge",  # merge, squash, or rebase
) -> dict:
    """Merge a pull request."""
    client = get_client()
    repo = client.get_repo(repo_name)
    pr = repo.get_pull(pr_number)

    result = pr.merge(
        commit_title=commit_title,
        commit_message=commit_message,
        merge_method=merge_method,
    )
    return {
        "merged": result.merged,
        "message": result.message,
        "sha": result.sha,
    }


def request_reviewers(
    repo_name: str,
    pr_number: int,
    reviewers: list[str] | None = None,
    team_reviewers: list[str] | None = None,
) -> dict:
    """Request reviewers for a PR."""
    client = get_client()
    repo = client.get_repo(repo_name)
    pr = repo.get_pull(pr_number)

    pr.create_review_request(
        reviewers=reviewers or [],
        team_reviewers=team_reviewers or [],
    )
    return _format_pr(pr)


def add_pr_review(
    repo_name: str,
    pr_number: int,
    body: str,
    event: str = "COMMENT",  # APPROVE, REQUEST_CHANGES, or COMMENT
) -> dict:
    """Add a review to a PR."""
    client = get_client()
    repo = client.get_repo(repo_name)
    pr = repo.get_pull(pr_number)

    review = pr.create_review(body=body, event=event)
    return {
        "id": review.id,
        "state": review.state,
        "body": review.body,
        "user": _format_user(review.user),
        "submitted_at": review.submitted_at.isoformat() if review.submitted_at else None,
    }


# ==================== Repository Operations ====================


def get_repo_labels(repo_name: str) -> list[dict]:
    """Get labels for a repository."""
    client = get_client()
    repo = client.get_repo(repo_name)

    return [
        {
            "name": l.name,
            "color": l.color,
            "description": l.description,
        }
        for l in repo.get_labels()
    ]


def create_repo_label(
    repo_name: str,
    name: str,
    color: str,
    description: str | None = None,
) -> dict:
    """Create a label in a repository."""
    client = get_client()
    repo = client.get_repo(repo_name)

    label = repo.create_label(name=name, color=color, description=description or "")
    return {
        "name": label.name,
        "color": label.color,
        "description": label.description,
    }


def get_repo_collaborators(repo_name: str) -> list[dict]:
    """Get collaborators for a repository."""
    client = get_client()
    repo = client.get_repo(repo_name)

    return [_format_user(c) for c in repo.get_collaborators()]


def get_repo_branches(repo_name: str) -> list[dict]:
    """Get branches for a repository."""
    client = get_client()
    repo = client.get_repo(repo_name)

    return [
        {
            "name": b.name,
            "protected": b.protected,
            "sha": b.commit.sha,
        }
        for b in repo.get_branches()
    ]


def get_issue(repo_name: str, issue_number: int) -> dict:
    """Get a specific issue."""
    client = get_client()
    repo = client.get_repo(repo_name)
    issue = repo.get_issue(issue_number)
    return _format_issue(issue)


def get_pull_request(repo_name: str, pr_number: int) -> dict:
    """Get a specific pull request."""
    client = get_client()
    repo = client.get_repo(repo_name)
    pr = repo.get_pull(pr_number)
    return _format_pr(pr)
