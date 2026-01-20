# Agent Guide for Synced Issues

This folder contains planning documents. The `issues/` folder contains synced GitHub issues.

## Reading Issues

```bash
# View the issue index
cat issues/README.md

# Read a specific issue
cat issues/42.md
```

## Issue File Structure

Each issue file contains:

1. **Header** - Status, created date, labels, assignees, milestone
2. **Description** - The issue body with any images
3. **Sub-Issues** - Child issues if this is a parent issue
4. **Comments** - Discussion thread
5. **Metadata** - JSON at the bottom (for machine parsing)

## Working on Issues

1. Read the issue file thoroughly
2. Check for related issues mentioned in the body or comments
3. Create a feature branch: `git checkout -b issue-42-description`
4. Implement the fix
5. Commit referencing the issue: `Fixes #42: Description`

## Image References

Images are stored in `issues/images/` and referenced with relative paths like `![alt](images/issue-42-1.png)`.

## Syncing

Issues are synced using:

```bash
python sync_issues.py
```

The sync is incremental - files only update when content changes.

## Tips

- The README.md index shows all issues sorted by number (newest first)
- Open issues are grouped by milestone
- The "Updated" column shows when GitHub last updated the issue
- Labels help categorize: look for `bug`, `enhancement`, etc.
