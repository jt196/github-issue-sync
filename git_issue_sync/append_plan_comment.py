#!/usr/bin/env python3
"""
Append or update a plan markdown file as a GitHub issue comment.

Usage:
    ./append_plan_comment.py ISSUE_NUMBER [--repo OWNER/REPO] [--plan-dir PATH] [--dry-run]
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile


MARKER = "<!-- plan-sync -->"


def run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        text=True,
        capture_output=True,
        check=False,
    )


def get_repo_root() -> str:
    proc = run(["git", "rev-parse", "--show-toplevel"])
    if proc.returncode == 0:
        return proc.stdout.strip()
    return os.getcwd()


def resolve_repo(explicit_repo: str | None) -> str | None:
    if explicit_repo:
        return explicit_repo
    proc = run(["gh", "repo", "view", "--json", "nameWithOwner", "-q", ".nameWithOwner"])
    if proc.returncode != 0:
        return None
    return proc.stdout.strip()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("issue_number", help="GitHub issue number (e.g. 123)")
    parser.add_argument("--repo", help="owner/repo (overrides gh default)", default=None)
    parser.add_argument(
        "--plan-dir",
        help="Directory containing plan markdown files",
        default=None,
    )
    parser.add_argument("--dry-run", action="store_true", help="Print actions only")
    args = parser.parse_args()

    repo_root = get_repo_root()
    plan_dir = args.plan_dir or os.path.join(repo_root, ".github/issue-sync/plans")
    plan_path = os.path.join(plan_dir, f"{args.issue_number}.md")

    if not os.path.exists(plan_path):
        print(f"Plan file not found: {plan_path}", file=sys.stderr)
        return 1

    with open(plan_path, "r", encoding="utf-8") as handle:
        plan_body = handle.read()

    if not plan_body.strip():
        print(f"Plan file is empty: {plan_path}", file=sys.stderr)
        return 1

    repo = resolve_repo(args.repo)
    if not repo:
        print("Unable to resolve repository. Provide --repo or run within a git repo.", file=sys.stderr)
        return 1

    issue_cmd = ["gh", "api", f"repos/{repo}/issues/{args.issue_number}"]
    if args.dry_run:
        print(f"Would verify issue exists: {' '.join(issue_cmd)}")
    else:
        issue_proc = run(issue_cmd)
        if issue_proc.returncode != 0:
            print(issue_proc.stderr.strip() or "Issue not found.", file=sys.stderr)
            return 1

    body = f"{MARKER}\n\n{plan_body}"

    comments_cmd = [
        "gh",
        "api",
        "--paginate",
        f"repos/{repo}/issues/{args.issue_number}/comments",
    ]

    if args.dry_run:
        print(f"Would fetch issue comments: {' '.join(comments_cmd)}")
        print(f"Would post or update comment for plan: {plan_path}")
        return 0

    comments_proc = run(comments_cmd)
    if comments_proc.returncode != 0:
        print(comments_proc.stderr.strip() or "Failed to fetch issue comments.", file=sys.stderr)
        return 1

    try:
        comments = json.loads(comments_proc.stdout)
    except json.JSONDecodeError:
        print("Failed to parse comment list from gh api output.", file=sys.stderr)
        return 1

    # gh api --paginate may return a list of dicts or a list of lists
    if isinstance(comments, list) and comments and isinstance(comments[0], list):
        flattened: list[dict] = []
        for batch in comments:
            if isinstance(batch, list):
                flattened.extend(item for item in batch if isinstance(item, dict))
        comments = flattened

    matching = [
        comment
        for comment in comments
        if isinstance(comment, dict) and MARKER in (comment.get("body") or "")
    ]
    matching.sort(key=lambda item: item.get("updated_at") or "")

    if matching:
        comment_id = matching[-1].get("id")
        if not comment_id:
            print("Matched comment missing id.", file=sys.stderr)
            return 1

        with tempfile.NamedTemporaryFile("w", delete=False, encoding="utf-8") as tmp:
            json.dump({"body": body}, tmp)
            tmp_path = tmp.name

        try:
            update_cmd = [
                "gh",
                "api",
                "-X",
                "PATCH",
                "--input",
                tmp_path,
                f"repos/{repo}/issues/comments/{comment_id}",
            ]
            update_proc = run(update_cmd)
            if update_proc.returncode != 0:
                print(update_proc.stderr.strip() or "Failed to update comment.", file=sys.stderr)
                return 1
        finally:
            try:
                os.remove(tmp_path)
            except OSError:
                pass

        print(f"Updated plan comment {comment_id} from {plan_path}")
        return 0

    with tempfile.NamedTemporaryFile("w", delete=False, encoding="utf-8") as tmp:
        tmp.write(body)
        tmp_path = tmp.name

    try:
        create_cmd = [
            "gh",
            "issue",
            "comment",
            args.issue_number,
            "--repo",
            repo,
            "--body-file",
            tmp_path,
        ]
        create_proc = run(create_cmd)
        if create_proc.returncode != 0:
            print(create_proc.stderr.strip() or "Failed to post comment.", file=sys.stderr)
            return 1
    finally:
        try:
            os.remove(tmp_path)
        except OSError:
            pass

    print(f"Posted plan comment from {plan_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
