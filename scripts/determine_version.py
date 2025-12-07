#!/usr/bin/env python3
"""Determine next version tag based on conventional commits.

This script is used by both CI workflow and local preview to determine
the next version that should be tagged. It uses python-semantic-release
to analyze conventional commits and determine the appropriate version bump.

Usage:
    python scripts/determine_version.py

Outputs to stdout:
    NEXT_VERSION=<version>
    NEW_TAG=v<version>
    BUMP_NEEDED=true|false
"""

import subprocess
import sys


def get_latest_tag():
    """Get the latest git tag."""
    result = subprocess.run(
        ["git", "describe", "--tags", "--abbrev=0"],
        capture_output=True,
        text=True,
    )
    tag = result.stdout.strip()
    return tag if tag else None


def main():
    """Main function - determines next version using semantic-release."""
    # Get latest tag
    latest_tag = get_latest_tag()
    if not latest_tag or latest_tag == "v0.1.0":
        latest_tag = None
        current_version = "0.1.0"
    else:
        current_version = latest_tag.replace("v", "")

    # Get commits since tag
    if latest_tag:
        result = subprocess.run(
            ["git", "rev-list", "--count", f"{latest_tag}..HEAD"],
            capture_output=True,
            text=True,
        )
        commits_count = int(result.stdout.strip() or "0")
    else:
        result = subprocess.run(
            ["git", "rev-list", "--count", "HEAD"],
            capture_output=True,
            text=True,
        )
        commits_count = int(result.stdout.strip() or "0")

    if commits_count == 0:
        # No commits, no version bump needed
        print(f"NEXT_VERSION={current_version}")
        print(f"NEW_TAG={latest_tag if latest_tag else 'v0.1.0'}")
        print("BUMP_NEEDED=false")
        sys.exit(0)

    # Use python-semantic-release to determine next version
    try:
        result = subprocess.run(
            ["python", "-m", "semantic_release", "version", "--print"],
            capture_output=True,
            text=True,
        )

        # Extract version from output (last line, remove warnings)
        output_lines = result.stdout.strip().split("\n")
        semantic_version = None

        for line in reversed(output_lines):
            import re

            version_match = re.search(r"^(\d+\.\d+\.\d+)$", line.strip())
            if version_match:
                semantic_version = version_match.group(1)
                break

        # Validate semantic-release suggestion
        if semantic_version and semantic_version != current_version:
            curr_parts = current_version.split(".")
            next_parts = semantic_version.split(".")

            # Validate: prevent invalid jumps (e.g., 0.6.0 -> 1.0.0 unless breaking change)
            if curr_parts[0] == "0" and next_parts[0] == "1":
                # Invalid: jumping from 0.x.x to 1.0.0
                print(
                    f"⚠️  Semantic-release suggested invalid jump from {current_version} to {semantic_version}",
                    file=sys.stderr,
                )
                semantic_version = None
            elif int(next_parts[0]) > int(curr_parts[0]) + 1:
                # Invalid: major version jumped by more than 1
                print("⚠️  Semantic-release suggested invalid major jump", file=sys.stderr)
                semantic_version = None

        if semantic_version and semantic_version != current_version:
            # Valid semantic-release suggestion
            print(f"NEXT_VERSION={semantic_version}")
            print(f"NEW_TAG=v{semantic_version}")
            print("BUMP_NEEDED=true")
            sys.exit(0)
        else:
            # No valid semantic bump detected - use fallback patch bump
            curr_parts = current_version.split(".")
            major = int(curr_parts[0])
            minor = int(curr_parts[1])
            patch = int(curr_parts[2]) + 1
            fallback_version = f"{major}.{minor}.{patch}"

            print(f"NEXT_VERSION={fallback_version}")
            print(f"NEW_TAG=v{fallback_version}")
            print("BUMP_NEEDED=true")
            sys.exit(0)

    except FileNotFoundError:
        print("Error: python-semantic-release not found", file=sys.stderr)
        print("Install it with: pip install python-semantic-release[all]", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error running semantic-release: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
