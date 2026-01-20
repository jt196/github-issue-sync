#!/usr/bin/env python3
"""
github-issue-sync: Sync GitHub issues to local markdown files.

Usage:
    python sync_issues.py [options]

Options:
    --repo OWNER/REPO    GitHub repository (overrides GITHUB_REPO env var)
    --force-images       Re-download all images even if they exist
    --sync-closed        Include closed issues in sync
    --dry-run            Show what would change without writing files
    --verbose, -v        Enable verbose logging

Environment Variables:
    GITHUB_REPO          Repository to sync (owner/repo format)
    OUTPUT_DIR           Output directory (default: issues)
    SYNC_CLOSED          Include closed issues (default: false)

See README.md for full documentation.
"""

from git_issue_sync.cli import main

if __name__ == "__main__":
    main()
