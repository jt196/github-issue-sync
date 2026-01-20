"""
GitHub API client using the gh CLI.

Uses the gh CLI tool for authentication and API access, avoiding the need
for separate token management.
"""

import json
import logging
import subprocess
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class GitHubClientError(Exception):
    """Error from GitHub API or gh CLI."""

    pass


def run_gh_command(args: List[str], timeout: int = 60) -> str:
    """
    Execute a gh CLI command and return the output.

    Args:
        args: Command arguments (without 'gh' prefix)
        timeout: Command timeout in seconds

    Returns:
        Command stdout as string

    Raises:
        GitHubClientError: If command fails
    """
    cmd = ["gh"] + args
    logger.debug(f"Running: {' '.join(cmd)}")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )

        if result.returncode != 0:
            error_msg = result.stderr.strip() or result.stdout.strip()
            raise GitHubClientError(f"gh command failed: {error_msg}")

        return result.stdout

    except subprocess.TimeoutExpired:
        raise GitHubClientError(f"Command timed out after {timeout}s")
    except FileNotFoundError:
        raise GitHubClientError(
            "gh CLI not found. Install from https://cli.github.com/"
        )


def get_auth_token() -> str:
    """
    Get the GitHub auth token from gh CLI.

    Returns:
        GitHub authentication token

    Raises:
        GitHubClientError: If not authenticated
    """
    try:
        token = run_gh_command(["auth", "token"]).strip()
        if not token:
            raise GitHubClientError("No auth token returned")
        return token
    except GitHubClientError as e:
        raise GitHubClientError(
            f"Not authenticated with gh CLI. Run 'gh auth login' first. Error: {e}"
        )


def fetch_issues_list(
    repo: str, include_closed: bool = False, limit: int = 1000
) -> List[Dict[str, Any]]:
    """
    Fetch all issues from a repository.

    Args:
        repo: Repository in owner/repo format
        include_closed: Whether to include closed issues
        limit: Maximum number of issues to fetch

    Returns:
        List of issue dictionaries
    """
    fields = [
        "number",
        "title",
        "body",
        "state",
        "labels",
        "assignees",
        "milestone",
        "createdAt",
        "updatedAt",
        "closedAt",
        "comments",
        "author",
    ]

    state = "all" if include_closed else "open"

    args = [
        "issue",
        "list",
        "--repo",
        repo,
        "--state",
        state,
        "--limit",
        str(limit),
        "--json",
        ",".join(fields),
    ]

    output = run_gh_command(args, timeout=120)
    return json.loads(output)


def fetch_issue_details(repo: str, issue_number: int) -> Dict[str, Any]:
    """
    Fetch additional issue details via REST API.

    This retrieves data not available through 'gh issue list', such as
    sub_issues_summary.

    Args:
        repo: Repository in owner/repo format
        issue_number: Issue number

    Returns:
        Issue details dictionary
    """
    args = ["api", f"/repos/{repo}/issues/{issue_number}"]
    output = run_gh_command(args)
    return json.loads(output)


def fetch_single_issue(repo: str, issue_number: int) -> Dict[str, Any]:
    """
    Fetch a single issue with full details via gh issue view.

    Args:
        repo: Repository in owner/repo format
        issue_number: Issue number

    Returns:
        Issue dictionary with same structure as fetch_issues_list
    """
    fields = [
        "number",
        "title",
        "body",
        "state",
        "labels",
        "assignees",
        "milestone",
        "createdAt",
        "updatedAt",
        "closedAt",
        "comments",
        "author",
    ]

    args = [
        "issue",
        "view",
        str(issue_number),
        "--repo",
        repo,
        "--json",
        ",".join(fields),
    ]

    output = run_gh_command(args)
    return json.loads(output)


def fetch_tracked_issues(
    owner: str, name: str, issue_number: int, limit: int = 50
) -> List[Dict[str, Any]]:
    """
    Fetch tracked (child) issues via GraphQL API.

    Args:
        owner: Repository owner
        name: Repository name
        issue_number: Parent issue number
        limit: Maximum tracked issues to fetch

    Returns:
        List of tracked issue dictionaries with number, title, state
    """
    query = f"""{{
      repository(owner: "{owner}", name: "{name}") {{
        issue(number: {issue_number}) {{
          trackedIssues(first: {limit}) {{
            nodes {{
              number
              title
              state
            }}
          }}
        }}
      }}
    }}"""

    args = ["api", "graphql", "-f", f"query={query}"]

    try:
        output = run_gh_command(args)
        data = json.loads(output)

        # Navigate the nested response
        nodes = (
            data.get("data", {})
            .get("repository", {})
            .get("issue", {})
            .get("trackedIssues", {})
            .get("nodes", [])
        )

        return nodes or []

    except (json.JSONDecodeError, GitHubClientError) as e:
        logger.warning(f"Failed to fetch tracked issues for #{issue_number}: {e}")
        return []
