"""GitHub integration endpoints for fetching notifications, issues, PRs."""

from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException, Request
from services import github

router = APIRouter(prefix="/github", tags=["github"])


def _require_auth(request: Request):
    """Check if user is authenticated to the app."""
    session_id = request.cookies.get("session_id")
    if not session_id:
        raise HTTPException(status_code=401, detail="Not authenticated to app")


def _require_github():
    """Check if GitHub is configured."""
    if not github.is_configured():
        raise HTTPException(status_code=503, detail="GitHub token not configured")


# ==================== Status ====================


@router.get("/status")
async def get_status(request: Request):
    """Check GitHub connection status."""
    _require_auth(request)

    if not github.is_configured():
        return {"configured": False, "error": "GitHub token not configured"}

    try:
        user = github.get_user()
        return {
            "configured": True,
            "connected": True,
            "user": user,
        }
    except Exception as e:
        return {"configured": True, "connected": False, "error": str(e)}


# ==================== Notifications ====================


@router.get("/notifications")
async def get_notifications(
    request: Request,
    all: bool = False,
    participating: bool = False,
    hours_back: int | None = None,
):
    """Get GitHub notifications."""
    _require_auth(request)
    _require_github()

    try:
        since = None
        if hours_back:
            since = datetime.now() - timedelta(hours=hours_back)

        notifications = github.get_notifications(
            all_notifications=all,
            participating=participating,
            since=since,
        )
        unread = [n for n in notifications if n["unread"]]

        return {
            "total": len(notifications),
            "unread": len(unread),
            "notifications": notifications,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/notifications/read")
async def mark_notifications_read(request: Request):
    """Mark all notifications as read."""
    _require_auth(request)
    _require_github()

    try:
        result = github.mark_notifications_read()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


# ==================== Issues ====================


@router.get("/issues/assigned")
async def get_assigned_issues(request: Request, state: str = "open"):
    """Get issues assigned to you."""
    _require_auth(request)
    _require_github()

    try:
        issues = github.get_assigned_issues(state=state)
        return {"count": len(issues), "issues": issues}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/issues/created")
async def get_created_issues(request: Request, state: str = "open"):
    """Get issues created by you."""
    _require_auth(request)
    _require_github()

    try:
        issues = github.get_created_issues(state=state)
        return {"count": len(issues), "issues": issues}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/issues/mentioned")
async def get_mentioned_issues(request: Request, state: str = "open"):
    """Get issues where you're mentioned."""
    _require_auth(request)
    _require_github()

    try:
        issues = github.get_mentioned_issues(state=state)
        return {"count": len(issues), "issues": issues}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


# ==================== Pull Requests ====================


@router.get("/prs/review-requests")
async def get_review_requests(request: Request):
    """Get PRs where your review is requested."""
    _require_auth(request)
    _require_github()

    try:
        prs = github.get_review_requests()
        return {"count": len(prs), "pull_requests": prs}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/prs/mine")
async def get_my_prs(request: Request, state: str = "open"):
    """Get PRs created by you."""
    _require_auth(request)
    _require_github()

    try:
        prs = github.get_user_prs(state=state)
        return {"count": len(prs), "pull_requests": prs}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


# ==================== Repositories ====================


@router.get("/repos")
async def get_repos(
    request: Request,
    type: str = "all",
    sort: str = "updated",
    limit: int = 30,
):
    """Get your repositories."""
    _require_auth(request)
    _require_github()

    try:
        repos = github.get_repos(type=type, sort=sort, limit=limit)
        return {"count": len(repos), "repositories": repos}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/repos/{owner}/{repo}/activity")
async def get_repo_activity(
    request: Request,
    owner: str,
    repo: str,
    limit: int = 20,
):
    """Get recent activity on a repository."""
    _require_auth(request)
    _require_github()

    try:
        activity = github.get_repo_activity(f"{owner}/{repo}", limit=limit)
        return activity
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


# ==================== Search ====================


@router.get("/search/issues")
async def search_issues(request: Request, q: str, limit: int = 20):
    """Search issues and PRs."""
    _require_auth(request)
    _require_github()

    try:
        results = github.search_issues(q, limit=limit)
        return {"query": q, "count": len(results), "results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/search/repos")
async def search_repos(request: Request, q: str, limit: int = 20):
    """Search repositories."""
    _require_auth(request)
    _require_github()

    try:
        results = github.search_repos(q, limit=limit)
        return {"query": q, "count": len(results), "results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


# ==================== Summary ====================


@router.get("/summary")
async def get_summary(request: Request, hours: int = 24):
    """Get a summary of GitHub updates in the last N hours."""
    _require_auth(request)
    _require_github()

    try:
        summary = github.get_updates_summary(hours=hours)
        return summary
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


# ==================== Issue Operations ====================


@router.get("/repos/{owner}/{repo}/issues/{issue_number}")
async def get_issue(request: Request, owner: str, repo: str, issue_number: int):
    """Get a specific issue."""
    _require_auth(request)
    _require_github()

    try:
        issue = github.get_issue(f"{owner}/{repo}", issue_number)
        return issue
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/repos/{owner}/{repo}/issues")
async def create_issue(
    request: Request,
    owner: str,
    repo: str,
    title: str,
    body: str | None = None,
    labels: list[str] | None = None,
    assignees: list[str] | None = None,
):
    """Create an issue in a repository."""
    _require_auth(request)
    _require_github()

    try:
        issue = github.create_issue(
            f"{owner}/{repo}",
            title=title,
            body=body,
            labels=labels,
            assignees=assignees,
        )
        return issue
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.patch("/repos/{owner}/{repo}/issues/{issue_number}")
async def update_issue(
    request: Request,
    owner: str,
    repo: str,
    issue_number: int,
    title: str | None = None,
    body: str | None = None,
    state: str | None = None,
    labels: list[str] | None = None,
    assignees: list[str] | None = None,
):
    """Update an issue."""
    _require_auth(request)
    _require_github()

    try:
        issue = github.update_issue(
            f"{owner}/{repo}",
            issue_number,
            title=title,
            body=body,
            state=state,
            labels=labels,
            assignees=assignees,
        )
        return issue
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/repos/{owner}/{repo}/issues/{issue_number}/close")
async def close_issue(request: Request, owner: str, repo: str, issue_number: int):
    """Close an issue."""
    _require_auth(request)
    _require_github()

    try:
        issue = github.close_issue(f"{owner}/{repo}", issue_number)
        return issue
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/repos/{owner}/{repo}/issues/{issue_number}/reopen")
async def reopen_issue(request: Request, owner: str, repo: str, issue_number: int):
    """Reopen an issue."""
    _require_auth(request)
    _require_github()

    try:
        issue = github.reopen_issue(f"{owner}/{repo}", issue_number)
        return issue
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/repos/{owner}/{repo}/issues/{issue_number}/comments")
async def get_issue_comments(request: Request, owner: str, repo: str, issue_number: int):
    """Get comments on an issue."""
    _require_auth(request)
    _require_github()

    try:
        comments = github.get_issue_comments(f"{owner}/{repo}", issue_number)
        return {"count": len(comments), "comments": comments}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/repos/{owner}/{repo}/issues/{issue_number}/comments")
async def add_issue_comment(
    request: Request,
    owner: str,
    repo: str,
    issue_number: int,
    body: str,
):
    """Add a comment to an issue."""
    _require_auth(request)
    _require_github()

    try:
        comment = github.add_issue_comment(f"{owner}/{repo}", issue_number, body)
        return comment
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/repos/{owner}/{repo}/issues/{issue_number}/labels")
async def add_labels(
    request: Request,
    owner: str,
    repo: str,
    issue_number: int,
    labels: list[str],
):
    """Add labels to an issue."""
    _require_auth(request)
    _require_github()

    try:
        issue = github.add_labels(f"{owner}/{repo}", issue_number, labels)
        return issue
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.delete("/repos/{owner}/{repo}/issues/{issue_number}/labels")
async def remove_labels(
    request: Request,
    owner: str,
    repo: str,
    issue_number: int,
    labels: list[str],
):
    """Remove labels from an issue."""
    _require_auth(request)
    _require_github()

    try:
        issue = github.remove_labels(f"{owner}/{repo}", issue_number, labels)
        return issue
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/repos/{owner}/{repo}/issues/{issue_number}/assignees")
async def assign_issue(
    request: Request,
    owner: str,
    repo: str,
    issue_number: int,
    assignees: list[str],
):
    """Assign users to an issue."""
    _require_auth(request)
    _require_github()

    try:
        issue = github.assign_issue(f"{owner}/{repo}", issue_number, assignees)
        return issue
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.delete("/repos/{owner}/{repo}/issues/{issue_number}/assignees")
async def unassign_issue(
    request: Request,
    owner: str,
    repo: str,
    issue_number: int,
    assignees: list[str],
):
    """Unassign users from an issue."""
    _require_auth(request)
    _require_github()

    try:
        issue = github.unassign_issue(f"{owner}/{repo}", issue_number, assignees)
        return issue
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


# ==================== PR Operations ====================


@router.get("/repos/{owner}/{repo}/pulls/{pr_number}")
async def get_pull_request(request: Request, owner: str, repo: str, pr_number: int):
    """Get a specific pull request."""
    _require_auth(request)
    _require_github()

    try:
        pr = github.get_pull_request(f"{owner}/{repo}", pr_number)
        return pr
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/repos/{owner}/{repo}/pulls")
async def create_pull_request(
    request: Request,
    owner: str,
    repo: str,
    title: str,
    head: str,
    base: str,
    body: str | None = None,
    draft: bool = False,
):
    """Create a pull request."""
    _require_auth(request)
    _require_github()

    try:
        pr = github.create_pull_request(
            f"{owner}/{repo}",
            title=title,
            head=head,
            base=base,
            body=body,
            draft=draft,
        )
        return pr
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.put("/repos/{owner}/{repo}/pulls/{pr_number}/merge")
async def merge_pull_request(
    request: Request,
    owner: str,
    repo: str,
    pr_number: int,
    commit_title: str | None = None,
    commit_message: str | None = None,
    merge_method: str = "merge",
):
    """Merge a pull request."""
    _require_auth(request)
    _require_github()

    try:
        result = github.merge_pull_request(
            f"{owner}/{repo}",
            pr_number,
            commit_title=commit_title,
            commit_message=commit_message,
            merge_method=merge_method,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/repos/{owner}/{repo}/pulls/{pr_number}/requested_reviewers")
async def request_reviewers(
    request: Request,
    owner: str,
    repo: str,
    pr_number: int,
    reviewers: list[str] | None = None,
    team_reviewers: list[str] | None = None,
):
    """Request reviewers for a PR."""
    _require_auth(request)
    _require_github()

    try:
        pr = github.request_reviewers(
            f"{owner}/{repo}",
            pr_number,
            reviewers=reviewers,
            team_reviewers=team_reviewers,
        )
        return pr
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/repos/{owner}/{repo}/pulls/{pr_number}/reviews")
async def add_pr_review(
    request: Request,
    owner: str,
    repo: str,
    pr_number: int,
    body: str,
    event: str = "COMMENT",
):
    """Add a review to a PR (APPROVE, REQUEST_CHANGES, or COMMENT)."""
    _require_auth(request)
    _require_github()

    try:
        review = github.add_pr_review(f"{owner}/{repo}", pr_number, body, event)
        return review
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


# ==================== Repository Management ====================


@router.get("/repos/{owner}/{repo}/labels")
async def get_repo_labels(request: Request, owner: str, repo: str):
    """Get labels for a repository."""
    _require_auth(request)
    _require_github()

    try:
        labels = github.get_repo_labels(f"{owner}/{repo}")
        return {"count": len(labels), "labels": labels}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/repos/{owner}/{repo}/labels")
async def create_repo_label(
    request: Request,
    owner: str,
    repo: str,
    name: str,
    color: str,
    description: str | None = None,
):
    """Create a label in a repository."""
    _require_auth(request)
    _require_github()

    try:
        label = github.create_repo_label(f"{owner}/{repo}", name, color, description)
        return label
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/repos/{owner}/{repo}/collaborators")
async def get_repo_collaborators(request: Request, owner: str, repo: str):
    """Get collaborators for a repository."""
    _require_auth(request)
    _require_github()

    try:
        collaborators = github.get_repo_collaborators(f"{owner}/{repo}")
        return {"count": len(collaborators), "collaborators": collaborators}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/repos/{owner}/{repo}/branches")
async def get_repo_branches(request: Request, owner: str, repo: str):
    """Get branches for a repository."""
    _require_auth(request)
    _require_github()

    try:
        branches = github.get_repo_branches(f"{owner}/{repo}")
        return {"count": len(branches), "branches": branches}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
