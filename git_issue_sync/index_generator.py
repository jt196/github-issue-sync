"""
Index generator for the README.md file.

Generates the master index with statistics, issue tables, and usage
instructions.
"""

from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set

from .issue_fetcher import Issue


def _format_date(iso_string: str) -> str:
    """Format ISO date string to readable format (M/D/YYYY)."""
    if not iso_string:
        return ""
    try:
        dt = datetime.fromisoformat(iso_string.replace("Z", "+00:00"))
        return dt.strftime("%-m/%-d/%Y")
    except (ValueError, AttributeError):
        return iso_string


def generate_index(
    issues: List[Issue],
    repo: str,
    issues_dir: Path,
    images_dir: Path,
) -> str:
    """
    Generate the master README.md index.

    Args:
        issues: List of all synced issues
        repo: Repository name for display
        issues_dir: Output directory path for issue files
        images_dir: Images directory path

    Returns:
        Complete markdown content for README.md
    """
    lines = []
    issues_dir_str = issues_dir.as_posix().rstrip("/")
    images_dir_str = images_dir.as_posix().rstrip("/")

    # Header
    lines.append(f"# GitHub Issues - {repo}")
    lines.append("")
    lines.append("**AUTO-GENERATED DOCUMENTATION** - Do not edit manually")
    lines.append("")
    lines.append(f"Last synced: {datetime.utcnow().isoformat()}Z")
    lines.append("")
    lines.append(f"Total issues: {len(issues)}")
    lines.append("")

    # Quick stats
    open_issues = [i for i in issues if i.state == "OPEN"]
    closed_issues = [i for i in issues if i.state == "CLOSED"]

    lines.append("## Quick Stats")
    lines.append("")
    lines.append(f"- **Open:** {len(open_issues)}")
    lines.append(f"- **Closed:** {len(closed_issues)}")
    lines.append(f"- **Total:** {len(issues)}")
    lines.append("")

    # All unique labels
    all_labels: Set[str] = set()
    for issue in issues:
        for label in issue.labels:
            all_labels.add(label.name)

    if all_labels:
        lines.append(f"**Labels:** {', '.join(sorted(all_labels))}")
        lines.append("")

    # All issues table
    lines.append("## All Issues")
    lines.append("")
    lines.append("| # | Title | State | Labels | Assignees | Comments | Updated |")
    lines.append("|---|-------|-------|--------|-----------|----------|---------|")

    # Sort by number descending (newest first)
    sorted_issues = sorted(issues, key=lambda i: i.number, reverse=True)

    for issue in sorted_issues:
        labels = ", ".join(l.name for l in issue.labels) or "-"
        assignees = ", ".join(a.login for a in issue.assignees) or "-"
        updated = _format_date(issue.updated_at)
        state_emoji = "🟢" if issue.state == "OPEN" else "⚪"
        comments = len(issue.comments)

        lines.append(
            f"| [{issue.number}]({issue.number}.md) | {issue.title} | "
            f"{state_emoji} {issue.state} | {labels} | {assignees} | "
            f"{comments} | {updated} |"
        )

    lines.append("")
    lines.append("---")
    lines.append("")

    # Open issues grouped by milestone
    if open_issues:
        lines.append("## Open Issues")
        lines.append("")

        # Group by milestone
        by_milestone: Dict[str, List[Issue]] = defaultdict(list)
        for issue in open_issues:
            milestone = issue.milestone.title if issue.milestone else "No Milestone"
            by_milestone[milestone].append(issue)

        # Sort milestones (No Milestone last)
        milestone_names = sorted(by_milestone.keys())
        if "No Milestone" in milestone_names:
            milestone_names.remove("No Milestone")
            milestone_names.append("No Milestone")

        for milestone in milestone_names:
            milestone_issues = by_milestone[milestone]
            lines.append(f"### {milestone}")
            lines.append("")

            for issue in milestone_issues:
                labels_str = " ".join(f"`{l.name}`" for l in issue.labels)
                lines.append(
                    f"- [#{issue.number}]({issue.number}.md): {issue.title} {labels_str}"
                )

            lines.append("")

    # Usage instructions
    lines.append("---")
    lines.append("")
    lines.append("## Usage with Claude")
    lines.append("")
    lines.append("### Reading Issues")
    lines.append("")
    lines.append("```bash")
    lines.append("# Read a specific issue")
    lines.append(f"cat {issues_dir_str}/33.md")
    lines.append("")
    lines.append("# View all open issues")
    lines.append(f"cat {issues_dir_str}/README.md")
    lines.append("```")
    lines.append("")
    lines.append("### Working on an Issue")
    lines.append("")
    lines.append(f"1. Read the issue file: `{issues_dir_str}/{{number}}.md`")
    lines.append(f"2. View screenshots (images are in `{images_dir_str}/`)")
    lines.append("3. Create a branch: `git checkout -b issue-{number}-description`")
    lines.append("4. Implement changes")
    lines.append("5. Reference issue in commit: `Fixes #{number}: Description`")
    lines.append("")
    lines.append("### Syncing Issues")
    lines.append("")
    lines.append("```bash")
    lines.append("# Sync issues from GitHub")
    lines.append("python sync_issues.py")
    lines.append("")
    lines.append("# Force re-download all images")
    lines.append("python sync_issues.py --force-images")
    lines.append("")
    lines.append("# Preview changes without writing")
    lines.append("python sync_issues.py --dry-run")
    lines.append("```")
    lines.append("")

    return "\n".join(lines)
