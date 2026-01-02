#!/usr/bin/env python3
"""Generate app/_version.py file with version information.

Standard Python approach: use setuptools-scm normally, or write explicit version.

Usage:
    python scripts/generate_version_file.py [VERSION]

    If VERSION is provided, write it directly.
    Otherwise, use setuptools-scm (reads from pyproject.toml config).

Environment Variables:
    BUILD_TIMESTAMP: ISO 8601 timestamp for build time (optional)
"""

import os
import sys


def write_version_file(version, build_timestamp=None):
    """Write version file using standard template from pyproject.toml."""
    # Get build timestamp from environment or use provided value
    if build_timestamp is None:
        build_timestamp = os.getenv("BUILD_TIMESTAMP", "Not set")

    template = '''"""Version and build information for the application."""

__version__ = "{version}"

# Build timestamp - set at build time
# Format: ISO 8601 (YYYY-MM-DDTHH:MM:SS+00:00)
__build_timestamp__ = "{build_timestamp}"
'''

    content = template.format(version=version, build_timestamp=build_timestamp)
    version_file = "app/_version.py"
    os.makedirs(os.path.dirname(version_file), exist_ok=True)

    with open(version_file, "w", encoding="utf-8") as f:
        f.write(content)


def main():
    """Main function."""
    # Get build timestamp from environment
    build_timestamp = os.getenv("BUILD_TIMESTAMP", "Not set")

    # If version provided as argument, use it directly
    if len(sys.argv) > 1:
        version = sys.argv[1]
        write_version_file(version, build_timestamp)
        print(version)
        return 0

    # Otherwise, use setuptools-scm (standard Python approach)
    try:
        import setuptools_scm

        # Get version from setuptools-scm
        version = setuptools_scm.get_version()

        # Write version file with build timestamp
        write_version_file(version, build_timestamp)

        print(version)
        return 0

    except ImportError:
        print("Error: setuptools-scm not installed", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    sys.exit(main())
