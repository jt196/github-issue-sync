"""
Image processor for downloading and rewriting image URLs.

Downloads GitHub-hosted images to local storage and rewrites URLs
in markdown content to point to local paths.
"""

import logging
import re
import time
from pathlib import Path
from typing import List, NamedTuple, Optional

import requests

from .github_client import get_auth_token

logger = logging.getLogger(__name__)


class ImageMatch(NamedTuple):
    """A matched image in markdown content."""

    full_match: str
    url: str
    alt: str


class ImageProcessor:
    """Processes images in markdown content."""

    # Matches both markdown and HTML image syntax
    IMAGE_REGEX = re.compile(
        r'!\[([^\]]*)\]\(([^)]+)\)|<img[^>]+src=["\']([^"\']+)["\'][^>]*>',
        re.IGNORECASE,
    )

    def __init__(
        self,
        images_dir: Path,
        force_download: bool = False,
        max_retries: int = 3,
    ):
        self.images_dir = images_dir
        self.force_download = force_download
        self.max_retries = max_retries
        self._auth_token: Optional[str] = None

    @property
    def auth_token(self) -> str:
        """Lazy-load auth token."""
        if self._auth_token is None:
            self._auth_token = get_auth_token()
        return self._auth_token

    def process_content(self, content: str, issue_number: int) -> str:
        """
        Extract, download images, and rewrite URLs in content.

        Args:
            content: Markdown content with image references
            issue_number: Issue number for naming downloaded files

        Returns:
            Content with image URLs rewritten to local paths
        """
        if not content:
            return ""

        # Find all images
        images = self._find_images(content)

        # Filter to GitHub-hosted images only
        github_images = [
            img
            for img in images
            if "github.com" in img.url or "githubusercontent.com" in img.url
        ]

        if github_images:
            logger.debug(f"Found {len(github_images)} GitHub images in issue #{issue_number}")

        # Ensure images directory exists
        self.images_dir.mkdir(parents=True, exist_ok=True)

        # Download and rewrite each image
        processed_content = content
        for i, img in enumerate(github_images, 1):
            local_filename = self._generate_filename(img.url, issue_number, i)
            local_path = self.images_dir / local_filename
            relative_path = f"images/{local_filename}"

            try:
                self._download_image(img.url, local_path)

                # Rewrite URL in content (convert to markdown format)
                new_markup = f"![{img.alt}]({relative_path})"
                processed_content = processed_content.replace(img.full_match, new_markup)

            except Exception as e:
                logger.warning(f"Failed to download {img.url}: {e}")
                # Keep original URL if download fails

        return processed_content

    def _find_images(self, content: str) -> List[ImageMatch]:
        """Find all image references in content."""
        images = []

        for match in self.IMAGE_REGEX.finditer(content):
            # match[1] = markdown alt text, match[2] = markdown url
            # match[3] = HTML src url
            url = match.group(2) or match.group(3)
            alt = match.group(1) or "Image"

            if url:
                images.append(
                    ImageMatch(
                        full_match=match.group(0),
                        url=url.strip(),
                        alt=alt.strip(),
                    )
                )

        return images

    def _generate_filename(self, url: str, issue_number: int, index: int) -> str:
        """Generate a local filename for an image."""
        # Extract extension from URL if present
        url_path = url.split("?")[0]  # Remove query params
        parts = url_path.split("/")
        last_part = parts[-1] if parts else ""

        # Check if last part has a valid extension
        if "." in last_part:
            ext_part = last_part.split(".")[-1].lower()
            if len(ext_part) <= 4 and ext_part.isalnum():
                ext = ext_part
            else:
                ext = "png"
        else:
            # Default to png for GitHub attachment URLs
            ext = "png"

        return f"issue-{issue_number}-{index}.{ext}"

    def _download_image(self, url: str, local_path: Path) -> None:
        """
        Download an image with retry logic.

        Args:
            url: Image URL
            local_path: Local path to save image

        Raises:
            Exception: If download fails after all retries
        """
        # Skip if file exists and not forcing
        if not self.force_download and local_path.exists():
            if local_path.stat().st_size > 0:
                logger.debug(f"Skipping existing: {local_path}")
                return

        logger.info(f"Downloading: {url}")

        headers = {
            "Authorization": f"token {self.auth_token}",
            "Accept": "application/octet-stream",
        }

        last_error = None
        for attempt in range(1, self.max_retries + 1):
            try:
                response = requests.get(
                    url,
                    headers=headers,
                    timeout=30,
                    allow_redirects=True,
                )
                response.raise_for_status()

                # Verify we got actual content
                if len(response.content) == 0:
                    raise ValueError("Downloaded file is empty")

                # Write to file
                local_path.write_bytes(response.content)
                logger.info(f"Saved: {local_path} ({len(response.content)} bytes)")
                return

            except Exception as e:
                last_error = e
                # Clean up failed download
                if local_path.exists():
                    try:
                        local_path.unlink()
                    except OSError:
                        pass

                if attempt < self.max_retries:
                    delay = (2**attempt)
                    logger.debug(f"Retry {attempt}/{self.max_retries} after {delay}s...")
                    time.sleep(delay)

        raise Exception(f"Failed after {self.max_retries} attempts: {last_error}")
