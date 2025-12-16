#!/usr/bin/env python3
"""Version management script with security enhancements.

This script updates version information in project files with proper security measures.
"""

import logging
import re
import shlex
import shutil
import subprocess
import sys
from pathlib import Path
from typing import List, Optional, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Constants
VERSION_PATTERN = r"^v\d+\.\d+\.\d+$"
VERSION_WITH_SUFFIX_PATTERN = r"^v\d+\.\d+\.\d+(\.dev\d+)?(\+.*)?$"
MAX_TAG_LENGTH = 50


def _run_git_command(args: List[str], cwd: Optional[str] = None) -> Tuple[bool, str]:
    """Safely run a git command with proper error handling.

    Args:
        args: List of command arguments
        cwd: Working directory (optional)

    Returns:
        Tuple of (success, output)
    """
    if not args or not all(isinstance(arg, str) for arg in args):
        raise ValueError("Invalid git command arguments")

    git_path = shutil.which("git")
    if not git_path:
        logger.error("Git is not installed or not in PATH")
        return False, "Git command not found"

    cmd = [git_path] + args

    try:
        logger.debug("Running git command: %s", " ".join(shlex.quote(arg) for arg in cmd))
        result = subprocess.run(
            # 30 second timeout
            cmd,
            capture_output=True,
            text=True,
            check=True,
            cwd=cwd,
            timeout=30,
            shell=False,
        )
        return True, result.stdout.strip()
    except subprocess.CalledProcessError as e:
        logger.error("Git command failed: %s", e.stderr.strip())
        return False, e.stderr.strip()
    except subprocess.TimeoutExpired:
        logger.error("Git command timed out")
        return False, "Command timed out"
    except Exception as e:
        logger.exception("Unexpected error running git command")
        return False, str(e)


def validate_version(version: str) -> bool:
    """Validate version string format.

    Args:
        version: Version string to validate (e.g., 'v1.2.3' or 'v1.2.3.dev1')

    Returns:
        bool: True if valid, False otherwise
    """
    if not version or not isinstance(version, str):
        return False
    if len(version) > MAX_TAG_LENGTH:
        return False
    # Accept both base version and version with dev/local suffix
    return bool(re.match(VERSION_PATTERN, version) or re.match(VERSION_WITH_SUFFIX_PATTERN, version))


def get_latest_git_tag() -> Optional[str]:
    """Get the latest git tag with proper validation.

    Returns:
        str: Latest valid version tag or None if not found
    """
    success, output = _run_git_command(["tag", "-l"])
    if not success:
        return None

    # Filter and validate tags
    valid_tags = []
    for tag in output.splitlines():
        tag = tag.strip()
        # Only accept base version tags (no dev/local suffixes)
        if re.match(VERSION_PATTERN, tag):
            try:
                # Convert version string to tuple of integers for proper sorting
                version_parts = tuple(map(int, tag[1:].split(".")))
                valid_tags.append((version_parts, tag))
            except (ValueError, IndexError):
                continue

    if not valid_tags:
        return None

    # Sort by version and return the latest
    valid_tags.sort()
    return valid_tags[-1][1]


def get_commits_after_tag(tag: str) -> int:
    """Get the number of commits after the given tag.

    Args:
        tag: Git tag to check

    Returns:
        int: Number of commits after the tag, or 0 if tag not found or error
    """
    success, output = _run_git_command(["rev-list", "--count", f"{tag}..HEAD"])
    if not success:
        return 0
    try:
        return int(output)
    except ValueError:
        return 0


def has_uncommitted_changes() -> bool:
    """Check if there are uncommitted changes in the working directory.

    Returns:
        bool: True if there are uncommitted changes, False otherwise
    """
    success, output = _run_git_command(["status", "--porcelain"])
    if not success:
        return False
    return bool(output.strip())


def update_pyproject_version(version: str) -> bool:
    """Update version in _version.py with validation.

    Args:
        version: Version string to set (e.g., 'v1.2.3' or '1.2.3' or '1.2.3.dev1+local')

    Returns:
        bool: True if update was successful, False otherwise
    """
    # For validation, check if it's a base version (needs 'v' prefix) or already has suffix
    if version.startswith("v"):
        version_for_validation = version
    elif re.match(r"^\d+\.\d+\.\d+(\.dev\d+)?(\+.*)?$", version):
        # Already has dev/local suffix, add 'v' prefix for validation
        version_for_validation = f"v{version}"
    else:
        # Base version without 'v', add it for validation
        version_for_validation = f"v{version}"

    is_valid = validate_version(version_for_validation)

    if not is_valid:
        logger.error("Invalid version format: %s", version)
        return False

    # Normalize version for file storage (remove 'v' prefix if present)
    normalized_version = version[1:] if version.startswith("v") else version

    # Update the version file that setuptools_scm writes to
    version_file = Path("app/_version.py")
    version_file.parent.mkdir(parents=True, exist_ok=True)
    version_file.write_text(f'__version__ = "{normalized_version}"\n')

    return True


def get_current_version() -> Optional[str]:
    """Get current version from _version.py with validation.

    Returns:
        str: Current version string or None if not found/invalid
    """
    version_path = Path("app") / "_version.py"
    try:
        if not version_path.exists() or not version_path.is_file():
            logger.debug("Version file not found: %s", version_path)
            return None

        with open(version_path, "r", encoding="utf-8") as f:
            content = f.read()
            match = re.search(r'__version__ = "(.*?)"', content)
            if match:
                version = match.group(1)
                # Add 'v' prefix for validation
                if validate_version(f"v{version}"):
                    return version
                logger.warning("Invalid version format in _version.py: %s", version)
    except (IOError, PermissionError) as exc:
        logger.error("Error reading version file: %s", exc)
    except Exception:
        logger.exception("Unexpected error getting current version")

    return None


def main() -> None:
    """Main function to update project version from git tags."""
    try:
        # Get the latest git tag
        latest_tag = get_latest_git_tag()
        current_version = get_current_version()

        logger.info("Current version: %s", current_version or "Not set")
        logger.info("Latest git tag: %s", latest_tag or "No valid tags found")

        if not latest_tag:
            logger.error("No valid version tags found in the repository")
            sys.exit(1)

        # Normalize base version (remove 'v' prefix if present)
        base_version = latest_tag[1:] if latest_tag.startswith("v") else latest_tag

        # Check for commits after tag and uncommitted changes
        commits_after = get_commits_after_tag(latest_tag)
        has_uncommitted = has_uncommitted_changes()

        # Build version string following PEP 440
        version_parts = [base_version]
        if commits_after > 0:
            version_parts.append(f".dev{commits_after}")
        if has_uncommitted:
            version_parts.append("+local")

        computed_version = "".join(version_parts)

        logger.info("Commits after tag: %d", commits_after)
        logger.info("Uncommitted changes: %s", "Yes" if has_uncommitted else "No")
        logger.info("Computed version: %s", computed_version)

        # Compare with current version (compare base versions, ignoring dev/local suffixes)
        if current_version:
            # Extract base version from current (remove .dev* and +* suffixes)
            current_base = re.sub(r"\.dev\d+.*$", "", current_version)
            current_base = re.sub(r"\+.*$", "", current_base)
            if current_base == base_version and current_version == computed_version:
                logger.info("Current version %s is already up to date", current_version)
                return

        # Update version file
        logger.info("Updating to version %s", computed_version)
        if update_pyproject_version(computed_version):
            logger.info("Successfully updated to version %s", computed_version)
        else:
            logger.error("Failed to update project files")
            sys.exit(1)

    except KeyboardInterrupt:
        logger.warning("Operation cancelled by user")
        sys.exit(130)  # Standard exit code for keyboard interrupt
    except Exception as exc:
        logger.exception("An unexpected error occurred: %s", str(exc))
        sys.exit(1)


if __name__ == "__main__":
    main()
