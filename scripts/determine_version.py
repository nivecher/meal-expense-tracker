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

import re
import subprocess
import sys


def get_latest_tag() -> str | None:
    """Get the latest git tag (e.g., v0.6.1) or None if no tags."""
    result = subprocess.run(
        ["git", "describe", "--tags", "--abbrev=0"],
        capture_output=True,
        text=True,
    )
    tag = result.stdout.strip()
    return tag or None


def _parse_semantic_release_output(output: str) -> str | None:
    """Extract the semantic version from semantic-release --print output."""
    if not output:
        return None

    for line in reversed(output.strip().split("\n")):
        candidate = line.strip()
        if re.fullmatch(r"\d+\.\d+\.\d+", candidate):
            return candidate
    return None


def _detect_bump_type(current_version: str, next_version: str) -> str:
    """Detect bump type (MAJOR/MINOR/PATCH/NONE) for logging/debugging."""
    try:
        curr_major, curr_minor, curr_patch = (int(x) for x in current_version.split("."))
        next_major, next_minor, next_patch = (int(x) for x in next_version.split("."))
    except ValueError:
        return "UNKNOWN"

    if next_major > curr_major:
        return "MAJOR"
    if next_minor > curr_minor:
        return "MINOR"
    if next_patch > curr_patch:
        return "PATCH"
    return "NONE"


def main() -> None:
    """Determine next version using python-semantic-release.

    Delegates bump logic entirely to semantic-release so that Conventional
    Commits drive versioning. This script only:

    - Determines the current version from the latest tag (or 0.1.0 if none)
    - Asks semantic-release for the next version
    - Compares current vs next to decide if a bump is needed
    - Prints NEXT_VERSION/NEW_TAG/BUMP_NEEDED for CI consumption
    """
    latest_tag = get_latest_tag()
    if not latest_tag:
        current_version = "0.1.0"
    else:
        current_version = latest_tag.lstrip("v")

    try:
        result = subprocess.run(
            ["python", "-m", "semantic_release", "version", "--print"],
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        print("Error: python-semantic-release not found", file=sys.stderr)
        print("Install it with: pip install python-semantic-release[all]", file=sys.stderr)
        sys.exit(1)
    except Exception as exc:
        print(f"Error running semantic-release: {exc}", file=sys.stderr)
        sys.exit(1)

    semantic_version = _parse_semantic_release_output(result.stdout)

    if not semantic_version:
        print("Error: semantic-release did not produce a version", file=sys.stderr)
        sys.exit(1)

    # Enforce 0.x semantics: do not allow bumps to 1.0.0+ while still on 0.x.
    try:
        curr_major_str, curr_minor_str, _ = current_version.split(".")
        next_major_str, next_minor_str, _ = semantic_version.split(".")
        curr_major = int(curr_major_str)
        curr_minor = int(curr_minor_str)
        next_major = int(next_major_str)
    except ValueError:
        curr_major = 0
        curr_minor = 0
        next_major = 0

    if curr_major == 0 and next_major >= 1:
        # Map proposed major bump to next minor within 0.x line.
        adjusted_minor = curr_minor + 1
        semantic_version = f"0.{adjusted_minor}.0"
        print(
            f"# adjusted_next_version={semantic_version} (prevented 0.x → {next_major}.x.y)",
            file=sys.stderr,
        )

    bump_type = _detect_bump_type(current_version, semantic_version)
    print(f"# current_version={current_version}", file=sys.stderr)
    print(f"# semantic_release_next={semantic_version}", file=sys.stderr)
    print(f"# bump_type={bump_type}", file=sys.stderr)

    if semantic_version == current_version:
        # No semantic bump – either no relevant commits or non-conventional messages.
        next_version = current_version
        new_tag = latest_tag if latest_tag else "v0.1.0"
        bump_needed = "false"
    else:
        next_version = semantic_version
        new_tag = f"v{semantic_version}"
        bump_needed = "true"

    print(f"NEXT_VERSION={next_version}")
    print(f"NEW_TAG={new_tag}")
    print(f"BUMP_NEEDED={bump_needed}")


if __name__ == "__main__":
    main()
