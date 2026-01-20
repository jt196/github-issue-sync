"""
Smart file writer with change detection.

Only writes files when content has actually changed, based on content hash
comparison. Also handles removal of closed issue files when configured.
"""

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Set

logger = logging.getLogger(__name__)


@dataclass
class WriteResult:
    """Result of a file write operation."""

    file_path: Path
    changed: bool
    reason: str


class FileWriter:
    """Writes issue files with change detection."""

    # Pattern to extract content hash from existing file
    HASH_PATTERN = re.compile(r"<!-- Content-Hash: ([a-f0-9]+) -->")

    def __init__(self, output_dir: Path, dry_run: bool = False):
        self.output_dir = output_dir
        self.dry_run = dry_run

        # Ensure output directory exists
        if not dry_run:
            output_dir.mkdir(parents=True, exist_ok=True)

    def write_issue_if_changed(
        self,
        issue_number: int,
        content: str,
        content_hash: str,
    ) -> WriteResult:
        """
        Write issue file only if content has changed.

        Args:
            issue_number: Issue number for filename
            content: Markdown content to write
            content_hash: Content hash for comparison

        Returns:
            WriteResult indicating if file was changed
        """
        file_path = self.output_dir / f"{issue_number}.md"

        # Check existing file for hash
        if file_path.exists():
            existing_hash = self._extract_hash(file_path)
            if existing_hash == content_hash:
                logger.debug(f"Unchanged: {file_path.name}")
                return WriteResult(
                    file_path=file_path,
                    changed=False,
                    reason="Content unchanged",
                )

        # Write the file
        if not self.dry_run:
            file_path.write_text(content, encoding="utf-8")

        action = "Would write" if self.dry_run else "Wrote"
        logger.info(f"{action}: {file_path.name}")

        return WriteResult(
            file_path=file_path,
            changed=True,
            reason="New file" if not file_path.exists() else "Content updated",
        )

    def write_index(self, content: str) -> WriteResult:
        """
        Write the README.md index file.

        The index is always rewritten since it contains timestamps.

        Args:
            content: Index markdown content

        Returns:
            WriteResult
        """
        file_path = self.output_dir / "README.md"

        if not self.dry_run:
            file_path.write_text(content, encoding="utf-8")

        action = "Would write" if self.dry_run else "Wrote"
        logger.info(f"{action}: {file_path.name}")

        return WriteResult(
            file_path=file_path,
            changed=True,
            reason="Index updated",
        )

    def remove_closed_issues(
        self,
        synced_issue_numbers: Set[int],
    ) -> List[Path]:
        """
        Remove files for issues that are no longer in the synced set.

        This is used when SYNC_CLOSED=false to delete files for issues
        that have been closed on GitHub.

        Args:
            synced_issue_numbers: Set of issue numbers that were synced

        Returns:
            List of removed file paths
        """
        removed = []

        # Find all numbered markdown files
        for file_path in self.output_dir.glob("*.md"):
            if file_path.name == "README.md":
                continue

            try:
                issue_number = int(file_path.stem)
            except ValueError:
                continue  # Not a numbered issue file

            if issue_number not in synced_issue_numbers:
                if not self.dry_run:
                    file_path.unlink()

                action = "Would remove" if self.dry_run else "Removed"
                logger.info(f"{action} closed issue: {file_path.name}")
                removed.append(file_path)

        return removed

    def _extract_hash(self, file_path: Path) -> Optional[str]:
        """Extract content hash from existing file."""
        try:
            content = file_path.read_text(encoding="utf-8")
            match = self.HASH_PATTERN.search(content)
            return match.group(1) if match else None
        except (OSError, UnicodeDecodeError):
            return None
