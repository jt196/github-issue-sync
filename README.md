# github-issue-sync

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

## Recommended Folder Structure

```bash
project-root/ 
    .github-issue-sync/ # cloned directory or submodule
    .github/ # default location OUTPUT_DIR will place the issue-sync/ folder
```

## Installation

Add to your project as a submodule:

```bash
git submodule add https://github.com/jt196/github-issue-sync .github-issue-sync
```

## Setup

1. **Install dependencies** (virtual environment recommended) in project root:

```bash
# Create and activate virtual environment (if one doesn't already exist)
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows

# Install dependencies
pip install -r .github-issue-sync/requirements.txt
```

1. **Authenticate with GitHub CLI** (if not already):

```bash
gh auth login
```

1. **Configure**:

```bash
# Initialize templates in your project
python .github-issue-sync/sync_issues.py --init

# Edit the project config in the script folder
# .github-issue-sync/.env
```

Advanced: If you need a different base, run init with an absolute
`OUTPUT_DIR` so the template folder seeds correctly.

Note: `--dry-run` still requires `GITHUB_REPO` to be set.

## Usage

Run from your project root so relative paths resolve correctly:

```bash
# Sync from project root
python .github-issue-sync/sync_issues.py

# Sync a single issue
python .github-issue-sync/sync_issues.py --issue 42

# With options
python .github-issue-sync/sync_issues.py --verbose          # Verbose output
python .github-issue-sync/sync_issues.py --dry-run          # Preview without writing
python .github-issue-sync/sync_issues.py --force-images     # Re-download all images
python .github-issue-sync/sync_issues.py --sync-closed      # Include closed issues

# Override repo from command line
python .github-issue-sync/sync_issues.py --repo owner/repo
```

## Configuration

Configure `.github-issue-sync/.env` in your project:

```bash
# Required: GitHub repository to sync
GITHUB_REPO=owner/repo

# Output directory base (default: .github)
OUTPUT_DIR=.github

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
├── .github-issue-sync/
│   └── .env                # Your configuration
├── .github/
│   └── issue-sync/
│       ├── issues/
│       │   ├── README.md   # Auto-generated index
│       │   ├── 1.md        # Issue files
│       │   ├── 2.md
│       │   ├── ...
│       │   └── images/     # Downloaded images
│       │       ├── issue-1-1.png
│       │       └── ...
│       └── plans/
│           └── plan-template.md
└── .github-issue-sync/      # Submodule (if using)
```

## Change Detection

The script computes a content hash for each issue based on:
- Title, state, labels, assignees, milestone
- Body content (after image processing)
- Comments

**Important:** The `updatedAt` timestamp is NOT included in the hash. This means if GitHub updates the timestamp but no actual content changed, your issue files won't be rewritten. The "Updated" column appears only in the README.md index.

## For AI Assistants

Agent instructions are in `AGENTS.md` (symlinked as `CLAUDE.md`).

The `issue-sync/` folder in this repo contains templates and agent files.
On first run, it gets copied to your project under `.github/issue-sync/`.

Configure agent behavior in `.env`:
```bash
# When agents should create plans: ask, always, never
PLANS_CREATE=ask
```

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
