# Agent Instructions

This project uses `git-issue-sync` to sync GitHub issues to local markdown files.

## Issue Files

Issues are synced to the `issues/` folder:

```
issues/
├── README.md           # Index of all issues
├── 42.md               # Individual issue files
└── images/             # Downloaded images
```

### Reading Issues

- **Index**: `issues/README.md` - all issues sorted by number, grouped by milestone
- **Single issue**: `issues/{number}.md` - full issue with description, comments, metadata

### Issue File Structure

Each issue file contains:
1. **Header** - Status, created date, labels, assignees, milestone
2. **Description** - Issue body with local image references
3. **Sub-Issues** - Child issues if this is a parent issue
4. **Comments** - Discussion thread
5. **Metadata** - JSON footer for machine parsing

## Working on Issues

1. Read the issue file: `issues/{number}.md`
2. Check for related issues in body/comments
3. Create branch: `git checkout -b issue-{number}-description`
4. Implement the fix
5. Commit with reference: `git commit -m "Fix #{number}: Description"`

## Plans

The `plans/` folder is for implementation plans before coding.

### When to Create a Plan

Check the `PLANS_CREATE` setting in `.env`:
- `ask` (default) - Ask the user if a plan is needed
- `always` - Always create a plan before implementation
- `never` - Skip plans, implement directly

### Plan Template

See `plans/plan-template.example.md` for the recommended format. Copy to `plans/plan-template.md` to customize for your project.

### General Guidelines

- Keep plans short and actionable
- Focus on what to change, not lengthy explanations
- Include file paths and function names
- Add a simple test/verification step

### When to Skip a Plan

- Typo fixes
- Single-line changes
- Issues with clear, specific instructions already

## Syncing Issues

```bash
# Sync all issues
python sync_issues.py

# Sync single issue
python sync_issues.py --issue 42

# Preview changes
python sync_issues.py --dry-run
```

## Configuration

See `.env` for settings. Key options:
- `GITHUB_REPO` - Repository to sync
- `SYNC_CLOSED` - Include closed issues (true/false)
- `PLANS_CREATE` - When to create plans (ask/always/never)
