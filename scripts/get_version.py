#!/usr/bin/env python3
"""Get current application version.

Behaviour:
- On main when building from a tag: return the clean tag version (e.g., 0.7.0).
- On other refs/branches: return a PEP 440 dev preview version based on the
  next semantic version and commit metadata, matching CI/tag logic.
"""

import os
import re
import subprocess
import sys


def get_current_branch() -> str:
    """Get current git branch name (or 'detached')."""
    result = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        branch = result.stdout.strip()
        return branch or "detached"
    return "detached"


def _has_uncommitted_changes() -> bool:
    """Return True if the working tree has uncommitted changes."""
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return False
    return bool(result.stdout.strip())


def _get_latest_tag() -> str | None:
    """Get the latest tag name (e.g., v0.6.10) or None."""
    try:
        subprocess.run(
            ["git", "fetch", "--tags", "--force"],
            capture_output=True,
            check=False,
        )
        result = subprocess.run(
            ["git", "describe", "--tags", "--abbrev=0"],
            capture_output=True,
            text=True,
            check=False,
        )
        tag = result.stdout.strip()
        return tag or None
    except Exception:
        return None


def _get_latest_tag_version() -> str | None:
    """Get the latest git tag version (without 'v' prefix)."""
    tag = _get_latest_tag()
    if not tag:
        return None
    return tag.lstrip("v")


def _get_short_sha() -> str:
    """Return short commit SHA for current HEAD."""
    result = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"],
        capture_output=True,
        text=True,
    )
    return result.stdout.strip() or "unknown"


def _get_commits_since_tag(latest_tag: str | None) -> int:
    """Return count of commits since the given tag (or entire history if none)."""
    if latest_tag:
        cmd = ["git", "rev-list", "--count", f"{latest_tag}..HEAD"]
    else:
        cmd = ["git", "rev-list", "--count", "HEAD"]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return 0

    try:
        return int(result.stdout.strip() or "0")
    except ValueError:
        return 0


def _sanitize_branch_name(branch: str) -> str:
    """Sanitize branch name for use in local version metadata."""
    return re.sub(r"[^A-Za-z0-9.]+", "-", branch)


def _get_next_version_from_determine_version() -> tuple[str | None, bool]:
    """Call scripts/determine_version.py and parse NEXT_VERSION / BUMP_NEEDED."""
    try:
        result = subprocess.run(
            ["python", "scripts/determine_version.py"],
            capture_output=True,
            text=True,
        )
    except Exception:
        return None, False

    if result.returncode != 0:
        return None, False

    next_version: str | None = None
    bump_needed: bool | None = None

    for line in result.stdout.strip().split("\n"):
        if line.startswith("NEXT_VERSION="):
            next_version = line.split("=", 1)[1]
        elif line.startswith("BUMP_NEEDED="):
            bump_needed = line.split("=", 1)[1] == "true"

    if next_version is None:
        return None, False

    return next_version, bool(bump_needed)


def _write_version_file(version: str) -> None:
    """Write app/_version.py using the standard template."""
    template = '''"""Version and build information for the application."""

__version__ = "{version}"

# Build timestamp - set at build time via environment variable
# Format: ISO 8601 (YYYY-MM-DDTHH:MM:SS+00:00)
import os

__build_timestamp__ = os.getenv("BUILD_TIMESTAMP", "Not set")
'''
    version_file = "app/_version.py"
    os.makedirs(os.path.dirname(version_file), exist_ok=True)
    with open(version_file, "w", encoding="utf-8") as file:
        file.write(template.format(version=version))


def main() -> int:
    """Entry point for the version helper."""
    current_branch = get_current_branch()

    # On main with HEAD exactly at a tag and a clean tree: use the clean tag version.
    if current_branch == "main" and not _has_uncommitted_changes():
        try:
            exact_tag_result = subprocess.run(
                ["git", "describe", "--tags", "--exact-match"],
                capture_output=True,
                text=True,
                check=False,
            )
            if exact_tag_result.returncode == 0 and exact_tag_result.stdout.strip():
                tag = exact_tag_result.stdout.strip()
                tag_version = tag.lstrip("v")
                _write_version_file(tag_version)
                print(tag_version)
                return 0
        except Exception:
            # Fall through to preview version logic if anything goes wrong.
            pass

    # For non-main (or main without a tag), compute a PEP 440 dev preview version.
    latest_tag = _get_latest_tag()

    if latest_tag:
        current_base_version = latest_tag.lstrip("v")
    else:
        current_base_version = "0.1.0"

    next_version, bump_needed = _get_next_version_from_determine_version()
    base_version = next_version if (next_version and bump_needed) else current_base_version

    commits_after_tag = _get_commits_since_tag(latest_tag)
    dev_counter = max(commits_after_tag, 1)
    short_sha = _get_short_sha()
    branch_meta = _sanitize_branch_name(current_branch)

    preview_version = f"{base_version}.dev{dev_counter}+g{short_sha}.branch.{branch_meta}"

    _write_version_file(preview_version)
    print(preview_version)
    return 0


if __name__ == "__main__":
    sys.exit(main())
