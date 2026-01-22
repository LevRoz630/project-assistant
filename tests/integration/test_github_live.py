"""Live integration tests for GitHub API.

Run with: pytest tests/integration/test_github_live.py -v -s
These tests hit the real GitHub API using your configured token.
"""

import os
import sys
from pathlib import Path

import pytest

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "backend"))

from dotenv import load_dotenv

# Load real .env file BEFORE importing anything that uses settings
env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(env_path, override=True)

# Clear the settings cache so it reloads from .env
from config import get_settings
get_settings.cache_clear()


@pytest.fixture(scope="module")
def github_service():
    """Get the GitHub service module."""
    # Reset the client so it uses new settings
    from services import github
    github._client = None

    if not github.is_configured():
        pytest.skip("GitHub token not configured")

    return github


class TestGitHubConnection:
    """Test GitHub connection and authentication."""

    def test_is_configured(self, github_service):
        """Test that GitHub is configured."""
        assert github_service.is_configured() is True

    def test_get_user(self, github_service):
        """Test getting authenticated user."""
        user = github_service.get_user()

        assert "login" in user
        assert "name" in user
        assert "email" in user
        assert "avatar_url" in user
        print(f"\nAuthenticated as: {user['login']} ({user['name']})")
        print(f"Public repos: {user['public_repos']}")


class TestGitHubIssues:
    """Test GitHub issues."""

    def test_get_assigned_issues(self, github_service):
        """Test getting assigned issues."""
        issues = github_service.get_assigned_issues(state="open")

        assert isinstance(issues, list)
        print(f"\nAssigned open issues: {len(issues)}")

        for issue in issues[:5]:
            print(f"  - [{issue['repo']}] #{issue['number']}: {issue['title']}")

    def test_get_created_issues(self, github_service):
        """Test getting created issues."""
        issues = github_service.get_created_issues(state="open")

        assert isinstance(issues, list)
        print(f"\nCreated open issues: {len(issues)}")

        for issue in issues[:5]:
            print(f"  - [{issue['repo']}] #{issue['number']}: {issue['title']}")

    def test_get_mentioned_issues(self, github_service):
        """Test getting mentioned issues."""
        issues = github_service.get_mentioned_issues(state="open")

        assert isinstance(issues, list)
        print(f"\nMentioned in issues: {len(issues)}")


class TestGitHubPullRequests:
    """Test GitHub pull requests."""

    def test_get_review_requests(self, github_service):
        """Test getting PRs where review is requested."""
        prs = github_service.get_review_requests()

        assert isinstance(prs, list)
        print(f"\nPRs awaiting your review: {len(prs)}")

        for pr in prs[:5]:
            repo = pr.get('repo', 'unknown')
            print(f"  - [{repo}] #{pr['number']}: {pr['title']}")

    def test_get_user_prs(self, github_service):
        """Test getting user's PRs."""
        prs = github_service.get_user_prs(state="open")

        assert isinstance(prs, list)
        print(f"\nYour open PRs: {len(prs)}")

        for pr in prs[:5]:
            repo = pr.get('repo', 'unknown')
            print(f"  - [{repo}] #{pr['number']}: {pr['title']}")


class TestGitHubRepos:
    """Test GitHub repositories."""

    def test_get_repos(self, github_service):
        """Test getting user repositories."""
        repos = github_service.get_repos(type="all", sort="updated", limit=10)

        assert isinstance(repos, list)
        assert len(repos) > 0
        print(f"\nRecent repositories ({len(repos)}):")

        for repo in repos[:10]:
            visibility = "private" if repo['private'] else "public"
            lang = repo['language'] or "N/A"
            print(f"  - {repo['full_name']} ({visibility}, {lang}, {repo['stars']} stars)")

    def test_get_repo_branches(self, github_service):
        """Test getting repository branches."""
        # Use the project-assistant repo
        repos = github_service.get_repos(limit=1)
        if not repos:
            pytest.skip("No repos found")

        repo_name = repos[0]['full_name']
        branches = github_service.get_repo_branches(repo_name)

        assert isinstance(branches, list)
        print(f"\nBranches in {repo_name}:")

        for branch in branches[:10]:
            protected = " (protected)" if branch['protected'] else ""
            print(f"  - {branch['name']}{protected}")

    def test_get_repo_labels(self, github_service):
        """Test getting repository labels."""
        repos = github_service.get_repos(limit=1)
        if not repos:
            pytest.skip("No repos found")

        repo_name = repos[0]['full_name']
        labels = github_service.get_repo_labels(repo_name)

        assert isinstance(labels, list)
        print(f"\nLabels in {repo_name}: {len(labels)}")

        for label in labels[:10]:
            print(f"  - {label['name']} (#{label['color']})")


class TestGitHubSearch:
    """Test GitHub search."""

    def test_search_issues(self, github_service):
        """Test searching issues."""
        # Search for issues in user's repos
        user = github_service.get_user()
        results = github_service.search_issues(f"author:{user['login']} is:issue", limit=5)

        assert isinstance(results, list)
        print(f"\nSearch results (your issues): {len(results)}")

        for item in results[:5]:
            print(f"  - [{item['repo']}] #{item['number']}: {item['title']}")

    def test_search_repos(self, github_service):
        """Test searching repositories."""
        results = github_service.search_repos("personal assistant", limit=5)

        assert isinstance(results, list)
        print(f"\nSearch results (repos): {len(results)}")

        for repo in results[:5]:
            print(f"  - {repo['full_name']} ({repo['stars']} stars)")


class TestGitHubWriteOperations:
    """Test GitHub write operations (creates real data!).

    Note: Requires 'issues:write' scope on the token.
    """

    TEST_REPO = "LevRoz630/project-assistant"

    @pytest.fixture
    def test_issue(self, github_service):
        """Create a test issue and clean up after."""
        from github.GithubException import GithubException

        try:
            # Create
            issue = github_service.create_issue(
                self.TEST_REPO,
                title="[TEST] Automated test issue - please ignore",
                body="This issue was created by the automated test suite.\nIt will be closed automatically.",
                labels=[],
            )
            print(f"\nCreated test issue #{issue['number']}")
        except GithubException as e:
            if "403" in str(e):
                pytest.skip("Token lacks 'issues:write' scope")
            raise

        yield issue

        # Cleanup - close the issue
        try:
            github_service.close_issue(self.TEST_REPO, issue['number'])
            print(f"Closed test issue #{issue['number']}")
        except Exception:
            pass  # Best effort cleanup

    def test_create_and_close_issue(self, github_service, test_issue):
        """Test creating and closing an issue."""
        assert test_issue['title'] == "[TEST] Automated test issue - please ignore"
        assert test_issue['state'] == "open"
        print(f"Issue URL: {test_issue['url']}")

    def test_add_comment_to_issue(self, github_service, test_issue):
        """Test adding a comment to an issue."""
        comment = github_service.add_issue_comment(
            self.TEST_REPO,
            test_issue['number'],
            "This is an automated test comment.",
        )

        assert comment['body'] == "This is an automated test comment."
        print(f"Added comment: {comment['url']}")

    def test_get_issue_comments(self, github_service, test_issue):
        """Test getting issue comments."""
        # First add a comment
        github_service.add_issue_comment(
            self.TEST_REPO,
            test_issue['number'],
            "Test comment for retrieval test.",
        )

        comments = github_service.get_issue_comments(self.TEST_REPO, test_issue['number'])

        assert isinstance(comments, list)
        assert len(comments) >= 1
        print(f"Found {len(comments)} comments on issue")

    def test_update_issue(self, github_service, test_issue):
        """Test updating an issue."""
        updated = github_service.update_issue(
            self.TEST_REPO,
            test_issue['number'],
            title="[TEST] Updated title - please ignore",
            body="Updated body content.",
        )

        assert updated['title'] == "[TEST] Updated title - please ignore"
        print(f"Updated issue title to: {updated['title']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
