"""Tests for the GitHub router."""

from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient


class TestGitHubStatus:
    """Tests for GitHub status endpoint."""

    def test_status_unauthenticated(self, client: TestClient):
        """Test status check without app authentication."""
        response = client.get("/github/status")
        assert response.status_code == 401

    def test_status_not_configured(
        self,
        authenticated_client: TestClient,
    ):
        """Test status when GitHub token not configured."""
        with patch("routers.github.github.is_configured") as mock_configured:
            mock_configured.return_value = False
            response = authenticated_client.get("/github/status")

        assert response.status_code == 200
        data = response.json()
        assert data["configured"] is False

    def test_status_connected(
        self,
        authenticated_client: TestClient,
    ):
        """Test status when GitHub is connected."""
        mock_user = {
            "login": "testuser",
            "name": "Test User",
            "email": "test@example.com",
            "avatar_url": "https://avatars.githubusercontent.com/u/12345",
            "public_repos": 10,
            "followers": 5,
            "following": 3,
        }

        with patch("routers.github.github.is_configured") as mock_configured:
            mock_configured.return_value = True
            with patch("routers.github.github.get_user") as mock_get_user:
                mock_get_user.return_value = mock_user
                response = authenticated_client.get("/github/status")

        assert response.status_code == 200
        data = response.json()
        assert data["configured"] is True
        assert data["connected"] is True
        assert data["user"]["login"] == "testuser"


class TestGitHubNotifications:
    """Tests for GitHub notifications endpoints."""

    def test_get_notifications(
        self,
        authenticated_client: TestClient,
    ):
        """Test getting notifications."""
        mock_notifications = [
            {
                "id": "1",
                "reason": "mention",
                "unread": True,
                "updated_at": "2024-01-15T10:00:00",
                "subject": {"title": "Test Issue", "type": "Issue", "url": "https://api.github.com/repos/user/repo/issues/1"},
                "repo": {"name": "repo", "full_name": "user/repo"},
            },
            {
                "id": "2",
                "reason": "review_requested",
                "unread": False,
                "updated_at": "2024-01-15T09:00:00",
                "subject": {"title": "Test PR", "type": "PullRequest", "url": "https://api.github.com/repos/user/repo/pulls/2"},
                "repo": {"name": "repo", "full_name": "user/repo"},
            },
        ]

        with patch("routers.github.github.is_configured") as mock_configured:
            mock_configured.return_value = True
            with patch("routers.github.github.get_notifications") as mock_get:
                mock_get.return_value = mock_notifications
                response = authenticated_client.get("/github/notifications")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert data["unread"] == 1

    def test_mark_notifications_read(
        self,
        authenticated_client: TestClient,
    ):
        """Test marking notifications as read."""
        with patch("routers.github.github.is_configured") as mock_configured:
            mock_configured.return_value = True
            with patch("routers.github.github.mark_notifications_read") as mock_mark:
                mock_mark.return_value = {"status": "marked_read"}
                response = authenticated_client.post("/github/notifications/read")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "marked_read"


class TestGitHubIssues:
    """Tests for GitHub issues endpoints."""

    def test_get_assigned_issues(
        self,
        authenticated_client: TestClient,
    ):
        """Test getting assigned issues."""
        mock_issues = [
            {
                "id": 1,
                "number": 42,
                "title": "Test Issue",
                "state": "open",
                "url": "https://github.com/user/repo/issues/42",
                "created_at": "2024-01-15T08:00:00",
                "updated_at": "2024-01-15T10:00:00",
                "user": {"login": "author", "name": "Author", "avatar_url": "https://example.com/avatar"},
                "assignees": [],
                "labels": ["bug"],
                "comments": 3,
                "repo": "user/repo",
                "is_pull_request": False,
            }
        ]

        with patch("routers.github.github.is_configured") as mock_configured:
            mock_configured.return_value = True
            with patch("routers.github.github.get_assigned_issues") as mock_get:
                mock_get.return_value = mock_issues
                response = authenticated_client.get("/github/issues/assigned")

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 1
        assert data["issues"][0]["title"] == "Test Issue"

    def test_get_specific_issue(
        self,
        authenticated_client: TestClient,
    ):
        """Test getting a specific issue."""
        mock_issue = {
            "id": 1,
            "number": 42,
            "title": "Test Issue",
            "state": "open",
            "url": "https://github.com/user/repo/issues/42",
            "created_at": "2024-01-15T08:00:00",
            "updated_at": "2024-01-15T10:00:00",
            "user": {"login": "author", "name": "Author", "avatar_url": "https://example.com/avatar"},
            "assignees": [],
            "labels": ["bug"],
            "comments": 3,
            "repo": "user/repo",
            "is_pull_request": False,
        }

        with patch("routers.github.github.is_configured") as mock_configured:
            mock_configured.return_value = True
            with patch("routers.github.github.get_issue") as mock_get:
                mock_get.return_value = mock_issue
                response = authenticated_client.get("/github/repos/user/repo/issues/42")

        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Test Issue"
        assert data["number"] == 42

    def test_create_issue(
        self,
        authenticated_client: TestClient,
    ):
        """Test creating an issue."""
        mock_issue = {
            "id": 1,
            "number": 43,
            "title": "New Issue",
            "state": "open",
            "url": "https://github.com/user/repo/issues/43",
            "created_at": "2024-01-15T10:00:00",
            "updated_at": "2024-01-15T10:00:00",
            "user": {"login": "testuser", "name": "Test User", "avatar_url": "https://example.com/avatar"},
            "assignees": [],
            "labels": ["bug", "urgent"],
            "comments": 0,
            "repo": "user/repo",
            "is_pull_request": False,
        }

        with patch("routers.github.github.is_configured") as mock_configured:
            mock_configured.return_value = True
            with patch("routers.github.github.create_issue") as mock_create:
                mock_create.return_value = mock_issue
                response = authenticated_client.post(
                    "/github/repos/user/repo/issues",
                    params={"title": "New Issue", "body": "Issue body", "labels": ["bug", "urgent"]},
                )

        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "New Issue"
        assert data["number"] == 43

    def test_close_issue(
        self,
        authenticated_client: TestClient,
    ):
        """Test closing an issue."""
        mock_issue = {
            "id": 1,
            "number": 42,
            "title": "Test Issue",
            "state": "closed",
            "url": "https://github.com/user/repo/issues/42",
            "created_at": "2024-01-15T08:00:00",
            "updated_at": "2024-01-15T10:00:00",
            "user": {"login": "author", "name": "Author", "avatar_url": "https://example.com/avatar"},
            "assignees": [],
            "labels": ["bug"],
            "comments": 3,
            "repo": "user/repo",
            "is_pull_request": False,
        }

        with patch("routers.github.github.is_configured") as mock_configured:
            mock_configured.return_value = True
            with patch("routers.github.github.close_issue") as mock_close:
                mock_close.return_value = mock_issue
                response = authenticated_client.post("/github/repos/user/repo/issues/42/close")

        assert response.status_code == 200
        data = response.json()
        assert data["state"] == "closed"

    def test_add_issue_comment(
        self,
        authenticated_client: TestClient,
    ):
        """Test adding a comment to an issue."""
        mock_comment = {
            "id": 1,
            "body": "This is a test comment",
            "user": {"login": "testuser", "name": "Test User", "avatar_url": "https://example.com/avatar"},
            "created_at": "2024-01-15T10:00:00",
            "url": "https://github.com/user/repo/issues/42#issuecomment-1",
        }

        with patch("routers.github.github.is_configured") as mock_configured:
            mock_configured.return_value = True
            with patch("routers.github.github.add_issue_comment") as mock_add:
                mock_add.return_value = mock_comment
                response = authenticated_client.post(
                    "/github/repos/user/repo/issues/42/comments",
                    params={"body": "This is a test comment"},
                )

        assert response.status_code == 200
        data = response.json()
        assert data["body"] == "This is a test comment"


class TestGitHubPRs:
    """Tests for GitHub pull request endpoints."""

    def test_get_review_requests(
        self,
        authenticated_client: TestClient,
    ):
        """Test getting PRs where review is requested."""
        mock_prs = [
            {
                "id": 1,
                "number": 10,
                "title": "Test PR",
                "state": "open",
                "url": "https://github.com/user/repo/pull/10",
                "created_at": "2024-01-15T08:00:00",
                "updated_at": "2024-01-15T10:00:00",
                "merged_at": None,
                "user": {"login": "author", "name": "Author", "avatar_url": "https://example.com/avatar"},
                "assignees": [],
                "reviewers": [{"login": "testuser", "name": "Test User", "avatar_url": "https://example.com/avatar"}],
                "labels": [],
                "draft": False,
                "mergeable": True,
                "additions": 10,
                "deletions": 5,
                "changed_files": 2,
                "repo": "user/repo",
            }
        ]

        with patch("routers.github.github.is_configured") as mock_configured:
            mock_configured.return_value = True
            with patch("routers.github.github.get_review_requests") as mock_get:
                mock_get.return_value = mock_prs
                response = authenticated_client.get("/github/prs/review-requests")

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 1
        assert data["pull_requests"][0]["title"] == "Test PR"

    def test_create_pull_request(
        self,
        authenticated_client: TestClient,
    ):
        """Test creating a pull request."""
        mock_pr = {
            "id": 1,
            "number": 11,
            "title": "New Feature",
            "state": "open",
            "url": "https://github.com/user/repo/pull/11",
            "created_at": "2024-01-15T10:00:00",
            "updated_at": "2024-01-15T10:00:00",
            "merged_at": None,
            "user": {"login": "testuser", "name": "Test User", "avatar_url": "https://example.com/avatar"},
            "assignees": [],
            "reviewers": [],
            "labels": [],
            "draft": False,
            "mergeable": True,
            "additions": 50,
            "deletions": 10,
            "changed_files": 5,
            "repo": "user/repo",
        }

        with patch("routers.github.github.is_configured") as mock_configured:
            mock_configured.return_value = True
            with patch("routers.github.github.create_pull_request") as mock_create:
                mock_create.return_value = mock_pr
                response = authenticated_client.post(
                    "/github/repos/user/repo/pulls",
                    params={"title": "New Feature", "head": "feature-branch", "base": "main", "body": "PR description"},
                )

        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "New Feature"
        assert data["number"] == 11

    def test_merge_pull_request(
        self,
        authenticated_client: TestClient,
    ):
        """Test merging a pull request."""
        mock_result = {
            "merged": True,
            "message": "Pull Request successfully merged",
            "sha": "abc123def456",
        }

        with patch("routers.github.github.is_configured") as mock_configured:
            mock_configured.return_value = True
            with patch("routers.github.github.merge_pull_request") as mock_merge:
                mock_merge.return_value = mock_result
                response = authenticated_client.put(
                    "/github/repos/user/repo/pulls/10/merge",
                    params={"merge_method": "squash"},
                )

        assert response.status_code == 200
        data = response.json()
        assert data["merged"] is True

    def test_add_pr_review(
        self,
        authenticated_client: TestClient,
    ):
        """Test adding a review to a PR."""
        mock_review = {
            "id": 1,
            "state": "APPROVED",
            "body": "Looks good!",
            "user": {"login": "testuser", "name": "Test User", "avatar_url": "https://example.com/avatar"},
            "submitted_at": "2024-01-15T10:00:00",
        }

        with patch("routers.github.github.is_configured") as mock_configured:
            mock_configured.return_value = True
            with patch("routers.github.github.add_pr_review") as mock_add:
                mock_add.return_value = mock_review
                response = authenticated_client.post(
                    "/github/repos/user/repo/pulls/10/reviews",
                    params={"body": "Looks good!", "event": "APPROVE"},
                )

        assert response.status_code == 200
        data = response.json()
        assert data["state"] == "APPROVED"


class TestGitHubRepos:
    """Tests for GitHub repository endpoints."""

    def test_get_repos(
        self,
        authenticated_client: TestClient,
    ):
        """Test getting user repositories."""
        mock_repos = [
            {
                "id": 1,
                "name": "repo1",
                "full_name": "user/repo1",
                "description": "Test repository",
                "url": "https://github.com/user/repo1",
                "private": False,
                "stars": 10,
                "language": "Python",
            },
            {
                "id": 2,
                "name": "repo2",
                "full_name": "user/repo2",
                "description": "Another repository",
                "url": "https://github.com/user/repo2",
                "private": True,
                "stars": 5,
                "language": "TypeScript",
            },
        ]

        with patch("routers.github.github.is_configured") as mock_configured:
            mock_configured.return_value = True
            with patch("routers.github.github.get_repos") as mock_get:
                mock_get.return_value = mock_repos
                response = authenticated_client.get("/github/repos")

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 2
        assert data["repositories"][0]["name"] == "repo1"

    def test_get_repo_labels(
        self,
        authenticated_client: TestClient,
    ):
        """Test getting repository labels."""
        mock_labels = [
            {"name": "bug", "color": "d73a4a", "description": "Something isn't working"},
            {"name": "enhancement", "color": "a2eeef", "description": "New feature or request"},
        ]

        with patch("routers.github.github.is_configured") as mock_configured:
            mock_configured.return_value = True
            with patch("routers.github.github.get_repo_labels") as mock_get:
                mock_get.return_value = mock_labels
                response = authenticated_client.get("/github/repos/user/repo/labels")

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 2
        assert data["labels"][0]["name"] == "bug"

    def test_get_repo_branches(
        self,
        authenticated_client: TestClient,
    ):
        """Test getting repository branches."""
        mock_branches = [
            {"name": "main", "protected": True, "sha": "abc123"},
            {"name": "develop", "protected": False, "sha": "def456"},
        ]

        with patch("routers.github.github.is_configured") as mock_configured:
            mock_configured.return_value = True
            with patch("routers.github.github.get_repo_branches") as mock_get:
                mock_get.return_value = mock_branches
                response = authenticated_client.get("/github/repos/user/repo/branches")

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 2
        assert data["branches"][0]["name"] == "main"


class TestGitHubSummary:
    """Tests for GitHub summary endpoint."""

    def test_get_summary(
        self,
        authenticated_client: TestClient,
    ):
        """Test getting updates summary."""
        mock_summary = {
            "period_hours": 24,
            "since": "2024-01-14T10:00:00",
            "unread_notifications": 5,
            "notifications_by_type": {
                "Issue": [{"id": "1", "subject": {"title": "Test"}}],
                "PullRequest": [{"id": "2", "subject": {"title": "PR Test"}}],
            },
            "review_requests": 2,
            "review_requests_list": [],
            "assigned_issues": 3,
            "assigned_issues_list": [],
        }

        with patch("routers.github.github.is_configured") as mock_configured:
            mock_configured.return_value = True
            with patch("routers.github.github.get_updates_summary") as mock_get:
                mock_get.return_value = mock_summary
                response = authenticated_client.get("/github/summary")

        assert response.status_code == 200
        data = response.json()
        assert data["unread_notifications"] == 5
        assert data["review_requests"] == 2


class TestGitHubSearch:
    """Tests for GitHub search endpoints."""

    def test_search_issues(
        self,
        authenticated_client: TestClient,
    ):
        """Test searching issues."""
        mock_results = [
            {
                "id": 1,
                "number": 42,
                "title": "Bug: Something broken",
                "state": "open",
                "url": "https://github.com/user/repo/issues/42",
                "created_at": "2024-01-15T08:00:00",
                "updated_at": "2024-01-15T10:00:00",
                "user": {"login": "author", "name": "Author", "avatar_url": "https://example.com/avatar"},
                "assignees": [],
                "labels": ["bug"],
                "comments": 3,
                "repo": "user/repo",
                "is_pull_request": False,
            }
        ]

        with patch("routers.github.github.is_configured") as mock_configured:
            mock_configured.return_value = True
            with patch("routers.github.github.search_issues") as mock_search:
                mock_search.return_value = mock_results
                response = authenticated_client.get("/github/search/issues?q=bug")

        assert response.status_code == 200
        data = response.json()
        assert data["query"] == "bug"
        assert data["count"] == 1

    def test_search_repos(
        self,
        authenticated_client: TestClient,
    ):
        """Test searching repositories."""
        mock_results = [
            {
                "id": 1,
                "name": "awesome-python",
                "full_name": "user/awesome-python",
                "description": "Curated list of Python packages",
                "url": "https://github.com/user/awesome-python",
                "private": False,
                "stars": 1000,
                "language": "Python",
            }
        ]

        with patch("routers.github.github.is_configured") as mock_configured:
            mock_configured.return_value = True
            with patch("routers.github.github.search_repos") as mock_search:
                mock_search.return_value = mock_results
                response = authenticated_client.get("/github/search/repos?q=awesome+python")

        assert response.status_code == 200
        data = response.json()
        assert data["query"] == "awesome python"
        assert data["count"] == 1
