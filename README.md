# git-issue-sync

Sync GitHub issues to local markdown files for use with AI coding assistants.

## Features

- Fetches issues from any GitHub repository via `gh` CLI
- Downloads images to local storage
- Generates individual markdown files per issue
- Creates a master index (README.md) with statistics and navigation
- Smart change detection - only rewrites files when content changes
- Handles closed issues (sync or delete based on config)

## Requirements

- Python 3.8+
- [GitHub CLI](https://cli.github.com/) (`gh`) - installed and authenticated

## Installation

### Option 1: Git Submodule (Recommended)

Add to your project as a submodule:

```bash
git submodule add https://github.com/jt196/git-issue-sync .git-issue-sync
```

### Option 2: Clone Directly

```bash
git clone https://github.com/jt196/git-issue-sync
```

## Setup

1. **Install dependencies** (virtual environment recommended):

```bash
# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt
# Or if using as submodule:
pip install -r .git-issue-sync/requirements.txt
```

1. **Authenticate with GitHub CLI** (if not already):

```bash
gh auth login
```

1. **Configure**:

```bash
# Copy example config
cp .env.example .env  # or .git-issue-sync/.env.example .env

# Edit .env with your repository
# GITHUB_REPO=owner/repo
```

## Usage

```bash
# Basic sync
python sync_issues.py
# Or if using as submodule:
python .git-issue-sync/sync_issues.py

# With options
python sync_issues.py --verbose          # Verbose output
python sync_issues.py --dry-run          # Preview without writing
python sync_issues.py --force-images     # Re-download all images
python sync_issues.py --sync-closed      # Include closed issues

# Override repo from command line
python sync_issues.py --repo owner/repo
```

## Configuration

Create a `.env` file in your project root:

```bash
# Required: GitHub repository to sync
GITHUB_REPO=owner/repo

# Output directory (default: issues)
OUTPUT_DIR=issues

# Sync behavior
# false (default): Only sync open issues, delete files when issues close
# true: Sync all issues including closed
SYNC_CLOSED=false

# Image retry attempts (default: 3)
IMAGE_RETRIES=3

# Logging level: DEBUG, INFO, WARNING, ERROR
LOG_LEVEL=INFO
```

## Output Structure

```
your-project/
├── .env                    # Your configuration
├── issues/
│   ├── README.md           # Auto-generated index
│   ├── 1.md                # Issue files
│   ├── 2.md
│   ├── ...
│   └── images/             # Downloaded images
│       ├── issue-1-1.png
│       └── ...
└── .git-issue-sync/        # Submodule (if using)
```

## Change Detection

The script computes a content hash for each issue based on:
- Title, state, labels, assignees, milestone
- Body content (after image processing)
- Comments

**Important:** The `updatedAt` timestamp is NOT included in the hash. This means if GitHub updates the timestamp but no actual content changed, your issue files won't be rewritten. The "Updated" column appears only in the README.md index.

## Working with Synced Issues

### For AI Assistants

Point your AI assistant to read issues:

```
Read issues/README.md for the issue index
Read issues/42.md for a specific issue
```

### Workflow

1. Sync issues: `python sync_issues.py`
2. Read an issue file
3. Create a branch: `git checkout -b issue-42-fix-bug`
4. Implement the fix
5. Commit with reference: `git commit -m "Fix #42: Description"`

## Troubleshooting

### "gh CLI not found"

Install the GitHub CLI: https://cli.github.com/

### "Not authenticated"

Run `gh auth login` to authenticate.

### "Repository not found"

Check your `GITHUB_REPO` in `.env` uses `owner/repo` format.

### Images not downloading

- Ensure you have access to the repository
- Try `--force-images` to re-download
- Check `gh auth status` for authentication

## License

MIT
