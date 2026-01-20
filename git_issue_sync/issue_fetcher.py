"""
Issue fetcher that orchestrates retrieving issues and their relationships.
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .config import Config
from .github_client import (
    fetch_issues_list,
    fetch_issue_details,
    fetch_single_issue,
    fetch_tracked_issues,
    GitHubClientError,
)

logger = logging.getLogger(__name__)


@dataclass
class SubIssuesSummary:
    """Summary of sub-issues for a parent issue."""

    total: int = 0
    completed: int = 0
    percent_completed: int = 0


@dataclass
class TrackedIssue:
    """A tracked (child) issue reference."""

    number: int
    title: str
    state: str  # "OPEN" or "CLOSED"


@dataclass
class Comment:
    """An issue comment."""

    author: str
    body: str
    created_at: str


@dataclass
class Label:
    """An issue label."""

    name: str


@dataclass
class Assignee:
    """An issue assignee."""

    login: str


@dataclass
class Milestone:
    """An issue milestone."""

    title: str


@dataclass
class Issue:
    """A GitHub issue with all fetched data."""

    number: int
    title: str
    body: str
    state: str  # "OPEN" or "CLOSED"
    labels: List[Label]
    assignees: List[Assignee]
    milestone: Optional[Milestone]
    created_at: str
    updated_at: str
    closed_at: Optional[str]
    author: str
    comments: List[Comment]
    sub_issues_summary: Optional[SubIssuesSummary] = None
    tracked_issues: List[TrackedIssue] = field(default_factory=list)

    @property
    def github_url(self) -> str:
        """URL to the issue on GitHub. Requires repo to be set externally."""
        # This will be set by the fetcher
        return getattr(self, "_github_url", "")

    @github_url.setter
    def github_url(self, value: str):
        self._github_url = value


def _parse_issue(raw: Dict[str, Any], repo: str) -> Issue:
    """Parse raw issue data from gh CLI into an Issue object."""
    labels = [Label(name=l.get("name", "")) for l in raw.get("labels", [])]
    assignees = [Assignee(login=a.get("login", "")) for a in raw.get("assignees", [])]

    milestone_data = raw.get("milestone")
    milestone = Milestone(title=milestone_data["title"]) if milestone_data else None

    comments = [
        Comment(
            author=c.get("author", {}).get("login", "unknown"),
            body=c.get("body", ""),
            created_at=c.get("createdAt", ""),
        )
        for c in raw.get("comments", [])
    ]

    author_data = raw.get("author")
    author = author_data.get("login", "unknown") if author_data else "unknown"

    issue = Issue(
        number=raw["number"],
        title=raw.get("title", ""),
        body=raw.get("body", "") or "",
        state=raw.get("state", "OPEN"),
        labels=labels,
        assignees=assignees,
        milestone=milestone,
        created_at=raw.get("createdAt", ""),
        updated_at=raw.get("updatedAt", ""),
        closed_at=raw.get("closedAt"),
        author=author,
        comments=comments,
    )

    issue.github_url = f"https://github.com/{repo}/issues/{issue.number}"

    return issue


class IssueFetcher:
    """Fetches issues from GitHub with relationship data."""

    def __init__(self, config: Config):
        self.config = config
        self.repo = config.github_repo
        self.owner = config.repo_owner
        self.name = config.repo_name

    def fetch_all_issues(self) -> List[Issue]:
        """
        Fetch all issues with relationships.

        Returns:
            List of Issue objects with sub-issues and tracked issues populated
        """
        logger.info(f"Fetching issues from {self.repo}...")

        # Fetch base issue list
        raw_issues = fetch_issues_list(
            self.repo, include_closed=self.config.sync_closed
        )

        logger.info(f"Found {len(raw_issues)} issues")

        # Parse and enrich issues
        issues = []
        for raw in raw_issues:
            issue = _parse_issue(raw, self.repo)
            self._enrich_with_relationships(issue)
            issues.append(issue)

        return issues

    def fetch_issue(self, issue_number: int) -> Issue:
        """
        Fetch a single issue with relationships.

        Args:
            issue_number: The issue number to fetch

        Returns:
            Issue object with sub-issues and tracked issues populated
        """
        logger.info(f"Fetching issue #{issue_number} from {self.repo}...")

        raw = fetch_single_issue(self.repo, issue_number)
        issue = _parse_issue(raw, self.repo)
        self._enrich_with_relationships(issue)

        return issue

    def _enrich_with_relationships(self, issue: Issue) -> None:
        """Add sub-issues and tracked issues data to an issue."""
        try:
            # Fetch additional details from REST API
            details = fetch_issue_details(self.repo, issue.number)

            # Parse sub_issues_summary if present
            summary_data = details.get("sub_issues_summary")
            if summary_data:
                issue.sub_issues_summary = SubIssuesSummary(
                    total=summary_data.get("total", 0),
                    completed=summary_data.get("completed", 0),
                    percent_completed=summary_data.get("percent_completed", 0),
                )

                # If there are sub-issues, fetch the tracked issues via GraphQL
                if issue.sub_issues_summary.total > 0:
                    tracked = fetch_tracked_issues(
                        self.owner, self.name, issue.number
                    )
                    issue.tracked_issues = [
                        TrackedIssue(
                            number=t.get("number", 0),
                            title=t.get("title", ""),
                            state=t.get("state", "OPEN"),
                        )
                        for t in tracked
                    ]

        except GitHubClientError as e:
            logger.warning(f"Failed to fetch relationships for #{issue.number}: {e}")
