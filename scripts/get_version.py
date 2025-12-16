#!/usr/bin/env python3
"""Get current application version using setuptools-scm.

Standard Python approach: use setuptools-scm normally, but on main branch
use tag version directly (matching CI/deploy behavior).

This aligns with:
- make version: shows tag version on main
- CI/deploy workflows: use tag version on main
- Other branches: use setuptools-scm (may show post versions)
"""

import subprocess
import sys


def get_current_branch():
    """Get current git branch name."""
    result = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        return result.stdout.strip()
    return ""


def get_latest_tag_version():
    """Get the latest git tag version (without 'v' prefix)."""
    try:
        # Fetch tags first
        subprocess.run(
            ["git", "fetch", "--tags", "--force"],
            capture_output=True,
            check=False,
        )

        # Get latest tag
        result = subprocess.run(
            ["git", "describe", "--tags", "--abbrev=0"],
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode == 0 and result.stdout.strip():
            tag = result.stdout.strip()
            # Remove 'v' prefix if present
            return tag.lstrip("v")

        return None
    except Exception:
        return None


def check_local_changes():
    """Check if there are uncommitted local changes."""
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        return bool(result.stdout.strip())
    return False


def main():
    """Main function - uses setuptools-scm or tag version on main.

    On main branch: use latest tag version directly (matches CI/deploy behavior).
    On other branches: use setuptools-scm (may show post versions for dev work).
    """
    current_branch = get_current_branch()

    # On main branch: use tag version directly (matches deploy workflow)
    if current_branch == "main":
        tag_version = get_latest_tag_version()
        if tag_version:
            # Write version file with tag version (matches deploy behavior)
            template = '''"""Version and build information for the application."""

__version__ = "{version}"

# Build timestamp - set at build time via environment variable
# Format: ISO 8601 (YYYY-MM-DDTHH:MM:SS+00:00)
import os

__build_timestamp__ = os.getenv("BUILD_TIMESTAMP", "Not set")
'''
            import os as os_module

            version_file = "app/_version.py"
            os_module.makedirs(os_module.path.dirname(version_file), exist_ok=True)
            with open(version_file, "w", encoding="utf-8") as f:
                f.write(template.format(version=tag_version))

            print(tag_version)
            return 0
            # Fall through to setuptools-scm if no tag found

    # Use setuptools-scm (standard Python approach)
    try:
        import setuptools_scm

        # Generate version file and get version string from git tags
        # Explicitly use no-guess-dev scheme to show current tag with post-release marker
        # This matches the pyproject.toml configuration
        version = setuptools_scm.get_version(
            version_scheme="no-guess-dev",
            write_to="app/_version.py",
            write_to_template='"""Version and build information for the application."""\n\n__version__ = "{version}"\n\n# Build timestamp - set at build time via environment variable\n# Format: ISO 8601 (YYYY-MM-DDTHH:MM:SS+00:00)\nimport os\n\n__build_timestamp__ = os.getenv("BUILD_TIMESTAMP", "Not set")\n',
        )

        # Print the version (this is the canonical output)
        print(version)

        # Optional: warn about uncommitted changes
        if check_local_changes():
            print(
                "⚠️  Uncommitted local changes detected (not reflected in version)",
                file=sys.stderr,
            )

        return 0

    except ImportError:
        # Fallback to git describe if setuptools-scm not available
        result = subprocess.run(
            ["git", "describe", "--tags", "--always"],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            version = result.stdout.strip().replace("v", "")
            print(version)
            print(
                "⚠️  setuptools-scm not installed. Install with: pip install setuptools-scm[toml]",
                file=sys.stderr,
            )
            return 0

        print("unknown", file=sys.stderr)
        print("❌ Could not determine version", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
