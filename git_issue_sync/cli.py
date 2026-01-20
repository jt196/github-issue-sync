"""
CLI module - main entry point and orchestration.

Coordinates the sync workflow: fetch, process, write.
"""

import logging
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

from .config import Config, load_config
from .file_writer import FileWriter
from .image_processor import ImageProcessor
from .index_generator import generate_index
from .issue_fetcher import IssueFetcher
from .markdown_generator import compute_content_hash, generate_issue_markdown


@dataclass
class SyncStats:
    """Statistics from a sync operation."""

    total_issues: int = 0
    files_written: int = 0
    files_unchanged: int = 0
    files_removed: int = 0
    images_processed: int = 0
    errors: List[str] = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []


def setup_logging(verbose: bool = False):
    """Configure logging for the CLI."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )


def run_sync(config: Config) -> SyncStats:
    """
    Run the full sync workflow.

    Args:
        config: Configuration object

    Returns:
        SyncStats with operation statistics
    """
    logger = logging.getLogger(__name__)
    stats = SyncStats()

    seed_project_templates(config)

    # Initialize components
    fetcher = IssueFetcher(config)
    image_processor = ImageProcessor(
        images_dir=config.images_dir,
        force_download=config.force_images,
        max_retries=config.image_retries,
    )
    file_writer = FileWriter(
        output_dir=config.issues_dir,
        dry_run=config.dry_run,
    )

    # Fetch issues (single or all)
    try:
        if config.single_issue:
            logger.info(f"Fetching issue #{config.single_issue} from {config.github_repo}...")
            issue = fetcher.fetch_issue(config.single_issue)
            issues = [issue]
        else:
            logger.info(f"Fetching issues from {config.github_repo}...")
            issues = fetcher.fetch_all_issues()
    except Exception as e:
        logger.error(f"Failed to fetch issues: {e}")
        stats.errors.append(str(e))
        return stats

    stats.total_issues = len(issues)
    logger.info(f"Found {len(issues)} issue(s)")

    if not issues:
        logger.info("No issues to sync")
        return stats

    # Process each issue
    logger.info("")
    logger.info("Processing issues...")

    for issue in issues:
        try:
            # Process images in body
            processed_body = image_processor.process_content(
                issue.body, issue.number
            )

            # Process images in comments
            processed_comments = [
                image_processor.process_content(c.body, issue.number)
                for c in issue.comments
            ]

            # Compute content hash
            content_hash = compute_content_hash(
                issue, processed_body, processed_comments
            )

            # Generate markdown
            content = generate_issue_markdown(
                issue, processed_body, processed_comments, content_hash
            )

            # Write file if changed
            result = file_writer.write_issue_if_changed(
                issue.number, content, content_hash
            )

            if result.changed:
                stats.files_written += 1
            else:
                stats.files_unchanged += 1

        except Exception as e:
            logger.warning(f"Error processing issue #{issue.number}: {e}")
            stats.errors.append(f"Issue #{issue.number}: {e}")

    # Remove closed issue files (when SYNC_CLOSED=false) - skip for single issue sync
    if not config.sync_closed and not config.single_issue:
        synced_numbers = {i.number for i in issues}
        removed = file_writer.remove_closed_issues(synced_numbers)
        stats.files_removed = len(removed)

    # Generate index (skip for single issue sync)
    if not config.single_issue:
        logger.info("")
        logger.info("Generating index...")
        index_content = generate_index(
            issues,
            config.github_repo,
            config.issues_dir,
            config.images_dir,
        )
        file_writer.write_index(index_content)

    return stats


def _detect_repo_from_git(cwd: Path) -> Optional[str]:
    """Return owner/repo from git remote.origin.url if available."""
    try:
        result = subprocess.run(
            ["git", "-C", str(cwd), "config", "--get", "remote.origin.url"],
            capture_output=True,
            text=True,
            check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None

    url = result.stdout.strip()
    if not url:
        return None

    path = ""
    if url.startswith("git@"):
        if ":" not in url:
            return None
        path = url.split(":", 1)[1]
    else:
        from urllib.parse import urlparse

        parsed = urlparse(url)
        if not parsed.netloc:
            return None
        path = parsed.path.lstrip("/")

    if path.endswith(".git"):
        path = path[:-4]
    parts = path.split("/")
    if len(parts) < 2:
        return None
    return f"{parts[0]}/{parts[1]}"


def _write_repo_to_env(env_path: Path, repo: str) -> None:
    """Update GITHUB_REPO in .env if it has the placeholder value."""
    lines = env_path.read_text().splitlines()
    updated = []
    replaced = False
    for line in lines:
        if line.startswith("GITHUB_REPO=") and line.endswith("owner/repo"):
            updated.append(f"GITHUB_REPO={repo}")
            replaced = True
        else:
            updated.append(line)
    if replaced:
        env_path.write_text("\n".join(updated) + "\n")


def seed_project_templates(
    config: Config,
) -> Tuple[bool, Optional[Path], Optional[str]]:
    """Copy default templates into the project if missing."""
    if config.dry_run:
        return False, None, None

    script_root = Path(__file__).resolve().parents[1]
    seed_root = script_root / "issue-sync"
    if not seed_root.exists():
        return False, None, None

    issue_sync_dir = config.issue_sync_dir
    seeded_issue_sync = False
    if not issue_sync_dir.exists():
        config.output_dir.mkdir(parents=True, exist_ok=True)
        shutil.copytree(seed_root, issue_sync_dir)
        seeded_issue_sync = True
    else:
        def copy_if_missing(source: Path, destination: Path) -> None:
            if not source.exists() or destination.exists():
                return
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, destination)

        copy_if_missing(
            seed_root / "plans" / "plan-template.md",
            config.plans_dir / "plan-template.md",
        )
        copy_if_missing(seed_root / "AGENTS.md", issue_sync_dir / "AGENTS.md")
        copy_if_missing(seed_root / "CLAUDE.md", issue_sync_dir / "CLAUDE.md")

    env_template = Path(__file__).resolve().parent / ".env.template"
    env_target = script_root / ".env"
    created_env = False
    detected_repo = None
    if env_template.exists() and not env_target.exists():
        shutil.copyfile(env_template, env_target)
        created_env = True
        detected_repo = _detect_repo_from_git(Path.cwd())
        if detected_repo:
            _write_repo_to_env(env_target, detected_repo)

    return seeded_issue_sync, (env_target if created_env else None), detected_repo



def main():
    """Main entry point."""
    try:
        config = load_config()
    except SystemExit:
        raise
    except Exception as e:
        print(f"Configuration error: {e}", file=sys.stderr)
        sys.exit(1)

    setup_logging(config.verbose)
    logger = logging.getLogger(__name__)

    if config.legacy_output_dir:
        logger.warning(
            "Legacy OUTPUT_DIR detected (%s). Using base directory: %s",
            config.legacy_output_dir,
            config.output_dir,
        )

    if config.init_only:
        seeded, env_path, detected_repo = seed_project_templates(config)
        if seeded:
            logger.info("Initialized templates in %s", config.issue_sync_dir)
        if env_path:
            logger.info("Created .env file in %s", env_path.parent)
            if detected_repo:
                logger.info("Set GITHUB_REPO to %s", detected_repo)
            else:
                logger.info("Please update GITHUB_REPO with your owner/repo")
        return

    if config.dry_run:
        logger.info("DRY RUN - no files will be written")
        logger.info("")

    # Run sync
    stats = run_sync(config)

    # Print summary
    logger.info("")
    logger.info("=" * 40)
    logger.info("Sync Complete")
    logger.info("=" * 40)
    logger.info(f"Total issues:    {stats.total_issues}")
    logger.info(f"Files written:   {stats.files_written}")
    logger.info(f"Files unchanged: {stats.files_unchanged}")

    if stats.files_removed:
        logger.info(f"Files removed:   {stats.files_removed}")

    if stats.errors:
        logger.info(f"Errors:          {len(stats.errors)}")
        for error in stats.errors:
            logger.warning(f"  - {error}")

    logger.info("")
    logger.info(f"Output: {config.issues_dir}")

    # Exit with error code if there were errors
    if stats.errors:
        sys.exit(1)
