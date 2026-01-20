"""
Configuration management for git-issue-sync.

Loads configuration from:
1. .env file (via python-dotenv)
2. Environment variables
3. Command-line arguments (highest priority)
"""

import argparse
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv


@dataclass
class Config:
    """Configuration for git-issue-sync."""

    # Required
    github_repo: str

    # Output paths
    output_dir: Path = field(default_factory=lambda: Path("issues"))
    images_subdir: str = "images"

    # Sync behavior
    sync_closed: bool = False

    # Image handling
    force_images: bool = False
    image_retries: int = 3

    # Runtime options
    dry_run: bool = False
    verbose: bool = False
    log_level: str = "INFO"
    single_issue: Optional[int] = None

    @property
    def images_dir(self) -> Path:
        """Full path to images directory."""
        return self.output_dir / self.images_subdir

    @property
    def repo_owner(self) -> str:
        """Extract owner from github_repo."""
        return self.github_repo.split("/")[0]

    @property
    def repo_name(self) -> str:
        """Extract repo name from github_repo."""
        return self.github_repo.split("/")[1]


def parse_bool(value: Optional[str], default: bool = False) -> bool:
    """Parse a string value to boolean."""
    if value is None:
        return default
    return value.lower() in ("true", "1", "yes", "on")


def load_config() -> Config:
    """
    Load configuration from .env file, environment variables, and CLI arguments.

    Priority (highest to lowest):
    1. Command-line arguments
    2. Environment variables
    3. .env file
    4. Default values
    """
    # Load .env file from current working directory
    load_dotenv()

    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description="Sync GitHub issues to local markdown files.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python sync_issues.py                    # Sync with .env settings
  python sync_issues.py --issue 42         # Sync only issue #42
  python sync_issues.py --verbose          # Verbose output
  python sync_issues.py --dry-run          # Preview changes without writing
  python sync_issues.py --force-images     # Re-download all images
        """,
    )

    parser.add_argument(
        "--repo",
        dest="github_repo",
        help="GitHub repository (owner/repo). Overrides GITHUB_REPO env var.",
    )
    parser.add_argument(
        "--output-dir",
        dest="output_dir",
        help="Output directory for issues. Default: issues",
    )
    parser.add_argument(
        "--force-images",
        action="store_true",
        help="Re-download all images even if they exist locally.",
    )
    parser.add_argument(
        "--sync-closed",
        action="store_true",
        help="Include closed issues in sync.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would change without writing files.",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging.",
    )
    parser.add_argument(
        "--issue",
        type=int,
        dest="single_issue",
        help="Sync only a specific issue number.",
    )

    args = parser.parse_args()

    # Build configuration with priority: CLI > env > defaults
    github_repo = args.github_repo or os.getenv("GITHUB_REPO")
    if not github_repo:
        parser.error(
            "GitHub repository is required. Set GITHUB_REPO in .env or use --repo"
        )

    # Validate repo format
    if "/" not in github_repo or len(github_repo.split("/")) != 2:
        parser.error(f"Invalid repository format: {github_repo}. Use owner/repo format.")

    output_dir = Path(args.output_dir or os.getenv("OUTPUT_DIR", "issues"))

    sync_closed = args.sync_closed or parse_bool(os.getenv("SYNC_CLOSED"), False)

    return Config(
        github_repo=github_repo,
        output_dir=output_dir,
        images_subdir=os.getenv("IMAGES_SUBDIR", "images"),
        sync_closed=sync_closed,
        force_images=args.force_images,
        image_retries=int(os.getenv("IMAGE_RETRIES", "3")),
        dry_run=args.dry_run,
        verbose=args.verbose,
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        single_issue=args.single_issue,
    )
