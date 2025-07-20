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
import toml

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Constants
VERSION_PATTERN = r"^v\d+\.\d+\.\d+$"
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
        version: Version string to validate (e.g., 'v1.2.3')

    Returns:
        bool: True if valid, False otherwise
    """
    if not version or not isinstance(version, str):
        return False
    if len(version) > MAX_TAG_LENGTH:
        return False
    return bool(re.match(VERSION_PATTERN, version))


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
        if validate_version(tag):
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


def update_pyproject_version(version: str) -> bool:
    """Update version in pyproject.toml with validation.

    Args:
        version: Version string to set (e.g., 'v1.2.3')

    Returns:
        bool: True if update was successful, False otherwise
    """
    if not validate_version(version):
        logger.error("Invalid version format: %s", version)
        return False

    pyproject_path = Path("pyproject.toml")
    if not pyproject_path.exists() or not pyproject_path.is_file():
        logger.error("pyproject.toml not found or is not a file")
        return False

    # Read current pyproject.toml
    pyproject = toml.load(pyproject_path)

    # Update Python version in mypy configuration
    if "tool" in pyproject and "mypy" in pyproject["tool"]:
        pyproject["tool"]["mypy"]["python_version"] = ".".join(version.split(".")[:2])

    # Write back to file
    with open(pyproject_path, "w") as f:
        toml.dump(pyproject, f)

    # Update the version file that setuptools_scm writes to
    version_file = Path("app/_version.py")
    version_file.parent.mkdir(parents=True, exist_ok=True)
    version_file.write_text(f'__version__ = "{version}"\n')

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

        # Normalize versions for comparison (remove 'v' prefix if present)
        normalized_latest = latest_tag[1:] if latest_tag.startswith("v") else latest_tag

        if current_version and normalized_latest == current_version:
            logger.info("Current version %s is already up to date", current_version)
            return

        # Update pyproject.toml
        logger.info("Updating to version %s", normalized_latest)
        if update_pyproject_version(normalized_latest):
            logger.info("Successfully updated to version %s", normalized_latest)
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
