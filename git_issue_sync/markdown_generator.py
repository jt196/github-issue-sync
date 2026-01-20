"""
Markdown generator for issue files.

Generates markdown content for individual issues and computes content hashes
for change detection.
"""

import hashlib
import json
from datetime import datetime
from typing import Any, Dict, List

from .issue_fetcher import Issue, Comment


def _format_date(iso_string: str) -> str:
    """Format ISO date string to readable format (M/D/YYYY)."""
    if not iso_string:
        return ""
    try:
        dt = datetime.fromisoformat(iso_string.replace("Z", "+00:00"))
        return dt.strftime("%-m/%-d/%Y")
    except (ValueError, AttributeError):
        return iso_string


def compute_content_hash(
    issue: Issue,
    processed_body: str,
    processed_comments: List[str],
) -> str:
    """
    Compute a hash of content that should trigger file rewrite.

    IMPORTANT: This excludes updatedAt to avoid unnecessary rewrites when
    only the update timestamp changes but no actual content changed.

    Args:
        issue: The issue object
        processed_body: Body after image processing
        processed_comments: Comment bodies after image processing

    Returns:
        16-character hex hash of content
    """
    hashable_data: Dict[str, Any] = {
        "number": issue.number,
        "title": issue.title,
        "state": issue.state,
        "labels": sorted([l.name for l in issue.labels]),
        "assignees": sorted([a.login for a in issue.assignees]),
        "milestone": issue.milestone.title if issue.milestone else None,
        "body": processed_body,
        "comments": [
            {
                "author": c.author,
                "body": body,
                "created": c.created_at,
            }
            for c, body in zip(issue.comments, processed_comments)
        ],
    }

    # Include sub-issues data
    if issue.sub_issues_summary:
        hashable_data["sub_issues"] = {
            "total": issue.sub_issues_summary.total,
            "completed": issue.sub_issues_summary.completed,
            "percent": issue.sub_issues_summary.percent_completed,
        }

    if issue.tracked_issues:
        hashable_data["tracked_issues"] = [
            {
                "number": ti.number,
                "title": ti.title,
                "state": ti.state,
            }
            for ti in issue.tracked_issues
        ]

    # Create stable JSON representation
    json_str = json.dumps(hashable_data, sort_keys=True, ensure_ascii=True)
    return hashlib.sha256(json_str.encode()).hexdigest()[:16]


def generate_issue_markdown(
    issue: Issue,
    processed_body: str,
    processed_comments: List[str],
    content_hash: str,
) -> str:
    """
    Generate markdown content for an issue.

    Note: Updated date is intentionally NOT included in the individual file.
    It appears only in the README.md index to avoid unnecessary file changes.

    Args:
        issue: The issue object
        processed_body: Body after image processing
        processed_comments: Comment bodies after image processing
        content_hash: Pre-computed content hash

    Returns:
        Complete markdown content for the issue file
    """
    lines = []

    # Header section
    lines.append("---")
    lines.append(f"# Issue #{issue.number}: {issue.title}")
    lines.append("")
    lines.append(f"**Status:** {issue.state.upper()}")
    lines.append(f"**Created:** {_format_date(issue.created_at)}")

    if issue.labels:
        labels_str = ", ".join(l.name for l in issue.labels)
        lines.append(f"**Labels:** {labels_str}")

    if issue.assignees:
        assignees_str = ", ".join(a.login for a in issue.assignees)
        lines.append(f"**Assignees:** {assignees_str}")

    if issue.milestone:
        lines.append(f"**Milestone:** {issue.milestone.title}")

    lines.append(f"**GitHub:** [View on GitHub]({issue.github_url})")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Description section
    lines.append("## Description")
    lines.append("")
    if processed_body:
        lines.append(processed_body)
    else:
        lines.append("_No description provided_")
    lines.append("")

    # Sub-issues section (if any)
    if issue.sub_issues_summary and issue.sub_issues_summary.total > 0:
        summary = issue.sub_issues_summary
        lines.append("## Sub-Issues")
        lines.append("")
        lines.append(
            f"**Progress:** {summary.completed}/{summary.total} "
            f"({summary.percent_completed}%)"
        )
        lines.append("")

        if issue.tracked_issues:
            for sub in issue.tracked_issues:
                icon = "🟢" if sub.state == "OPEN" else "⚪"
                lines.append(f"- {icon} [#{sub.number}]({sub.number}.md): {sub.title}")

        lines.append("")

    # Comments section (if any)
    if issue.comments and processed_comments:
        lines.append(f"## Comments ({len(issue.comments)})")
        lines.append("")

        for comment, processed_body in zip(issue.comments, processed_comments):
            comment_date = _format_date(comment.created_at)
            lines.append(f"### {comment.author} - {comment_date}")
            lines.append("")
            lines.append(processed_body)
            lines.append("")
            lines.append("---")
            lines.append("")

    # Metadata footer
    metadata = {
        "number": issue.number,
        "title": issue.title,
        "state": issue.state,
        "labels": [l.name for l in issue.labels],
        "assignees": [a.login for a in issue.assignees],
        "milestone": issue.milestone.title if issue.milestone else None,
        "created": issue.created_at,
        "updated": issue.updated_at,
        "closed": issue.closed_at,
        "author": issue.author,
        "commentCount": len(issue.comments),
        "githubUrl": issue.github_url,
    }

    if issue.sub_issues_summary:
        metadata["subIssues"] = {
            "total": issue.sub_issues_summary.total,
            "completed": issue.sub_issues_summary.completed,
            "percent_completed": issue.sub_issues_summary.percent_completed,
        }

    if issue.tracked_issues:
        metadata["trackedIssues"] = [
            {"number": ti.number, "title": ti.title, "state": ti.state}
            for ti in issue.tracked_issues
        ]

    lines.append("<!-- AUTO-GENERATED: DO NOT EDIT MANUALLY -->")
    lines.append(f"<!-- Content-Hash: {content_hash} -->")
    lines.append(f"<!-- Last synced: {datetime.utcnow().isoformat()}Z -->")
    lines.append(f"<!-- Metadata: {json.dumps(metadata)} -->")

    return "\n".join(lines)
