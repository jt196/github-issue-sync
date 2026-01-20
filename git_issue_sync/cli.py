"""
CLI module - main entry point and orchestration.

Coordinates the sync workflow: fetch, process, write.
"""

import logging
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List

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


def seed_project_templates(config: Config) -> None:
    """Copy default templates into the project if missing."""
    if config.dry_run:
        return

    seed_root = Path(__file__).resolve().parents[1] / "issue-sync"
    if not seed_root.exists():
        return

    issue_sync_dir = config.issue_sync_dir
    if not issue_sync_dir.exists():
        config.output_dir.mkdir(parents=True, exist_ok=True)
        shutil.copytree(seed_root, issue_sync_dir)
        return

    plan_template = seed_root / "plans" / "plan-template.md"
    if not plan_template.exists():
        return

    dest_template = config.plans_dir / "plan-template.md"
    if dest_template.exists():
        return

    config.plans_dir.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(plan_template, dest_template)


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
