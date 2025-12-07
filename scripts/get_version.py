#!/usr/bin/env python3
"""Get current application version using setuptools-scm.

This is a simple wrapper that uses setuptools-scm's built-in version generation.
The version string itself contains all the information (commits since tag, date, hash).
"""

import subprocess
import sys


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
    """Main function - uses setuptools-scm to get version from git tags.

    setuptools-scm automatically handles:
    - Tagged commits: shows the tag version (e.g., 0.6.1)
    - Post-tag commits: shows tag.postN.devM+hash.date (e.g., 0.6.1.post1.dev3+gabc123.d20251207)
    - Local/branch changes: includes commit hash and date
    """
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
