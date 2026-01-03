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

# Constants
DEFAULT_VERSION = "0.1.0"
VERSION_PATTERN = re.compile(r"^\d+\.\d+\.\d+$")
BUMP_PRIORITY = {"major": 3, "minor": 2, "patch": 1}

# Expected "no bump" messages from semantic-release
EXPECTED_NO_BUMP_MESSAGES = [
    "no version change",
    "nothing to commit",
    "no release",
    "no commits",
]


def get_latest_tag() -> str | None:
    """Get the latest git tag (e.g., v0.6.1) or None if no tags exist.

    Returns:
        Latest git tag with 'v' prefix, or None if no tags found.
    """
    result = subprocess.run(
        ["git", "describe", "--tags", "--abbrev=0"],
        capture_output=True,
        text=True,
        check=False,
    )
    tag = result.stdout.strip()
    return tag if tag else None


def _parse_semantic_release_output(output: str) -> str | None:
    """Extract the semantic version from semantic-release --print output.

    Args:
        output: The stdout output from semantic-release command.

    Returns:
        Parsed version string (e.g., "0.6.10") or None if not found.
    """
    if not output:
        return None

    for line in reversed(output.strip().split("\n")):
        candidate = line.strip()
        if VERSION_PATTERN.fullmatch(candidate):
            return candidate
    return None


def _detect_bump_type(current_version: str, next_version: str) -> str:
    """Detect bump type (MAJOR/MINOR/PATCH/NONE) for logging/debugging.

    Args:
        current_version: Current version string (e.g., "0.6.10").
        next_version: Next version string (e.g., "0.7.0").

    Returns:
        Bump type: "MAJOR", "MINOR", "PATCH", or "NONE".
    """
    try:
        curr_parts = [int(x) for x in current_version.split(".")]
        next_parts = [int(x) for x in next_version.split(".")]
    except ValueError:
        return "UNKNOWN"

    if len(curr_parts) != 3 or len(next_parts) != 3:
        return "UNKNOWN"

    if next_parts[0] > curr_parts[0]:
        return "MAJOR"
    if next_parts[1] > curr_parts[1]:
        return "MINOR"
    if next_parts[2] > curr_parts[2]:
        return "PATCH"
    return "NONE"


def _get_commits_since_tag(tag: str | None) -> list[str]:
    """Get commit messages since the given tag.

    Args:
        tag: Git tag to compare against, or None for all commits.

    Returns:
        List of commit message subjects (first line only).
    """
    if not tag:
        # Get all commits
        result = subprocess.run(
            ["git", "log", "--format=%s", "--reverse"],
            capture_output=True,
            text=True,
            check=False,
        )
    else:
        # Get commits since tag
        result = subprocess.run(
            ["git", "log", f"{tag}..HEAD", "--format=%s", "--reverse"],
            capture_output=True,
            text=True,
            check=False,
        )

    if result.returncode != 0:
        return []

    return [line.strip() for line in result.stdout.strip().split("\n") if line.strip()]


def _parse_conventional_commit(commit_msg: str) -> str | None:
    """Parse a conventional commit message and return bump level.

    Follows Conventional Commits spec:
    - feat: minor bump
    - fix: patch bump
    - feat!: major bump (breaking change)
    - Any type with !: major bump
    - chore, refactor, docs, style, test: no bump (unless breaking)

    Args:
        commit_msg: Commit message to parse.

    Returns:
        Bump level: "major", "minor", "patch", or None if no bump.
    """
    # Skip merge commits
    if commit_msg.startswith("Merge "):
        return None

    # Check for breaking change indicator
    if "!" in commit_msg.split(":")[0] or "BREAKING CHANGE" in commit_msg:
        return "major"

    # Parse commit type
    if ":" in commit_msg:
        commit_type = commit_msg.split(":")[0].lower().strip()

        if commit_type == "feat":
            return "minor"
        if commit_type == "fix":
            return "patch"
        # Other types (chore, refactor, docs, etc.) don't trigger bumps
        # unless they have breaking change indicators (handled above)

    return None


def _analyze_commits_with_semantic_release(current_version: str) -> str | None:
    """Analyze commits since last tag and determine next version.

    This bypasses branch restrictions and analyzes commits directly using
    conventional commit format parsing.

    Args:
        current_version: Current version string (e.g., "0.6.10").

    Returns:
        Next version string (e.g., "0.7.0") or None if no bump needed.
    """
    try:
        # Get commits since last tag
        latest_tag = get_latest_tag()
        commits = _get_commits_since_tag(latest_tag)

        if not commits:
            return None

        # Parse commits to determine bump levels
        bump_levels = []
        for commit_msg in commits:
            bump_level = _parse_conventional_commit(commit_msg)
            if bump_level:
                bump_levels.append(bump_level)

        if not bump_levels:
            return None

        # Determine the maximum bump level (major > minor > patch)
        max_bump = max(bump_levels, key=lambda x: BUMP_PRIORITY.get(x, 0))

        # Calculate next version
        parts = [int(x) for x in current_version.split(".")]
        if len(parts) != 3:
            return None

        if max_bump == "major":
            next_version = f"{parts[0] + 1}.0.0"
        elif max_bump == "minor":
            next_version = f"{parts[0]}.{parts[1] + 1}.0"
        else:  # patch
            next_version = f"{parts[0]}.{parts[1]}.{parts[2] + 1}"

        print(
            f"# Analyzed {len(commits)} commits, found {len(bump_levels)} conventional commits",
            file=sys.stderr,
        )
        print(f"# Max bump level: {max_bump}", file=sys.stderr)
        return next_version

    except Exception as exc:
        print(f"# Warning: Failed to analyze commits: {exc}", file=sys.stderr)
        return None


def _validate_version_format(version: str) -> bool:
    """Validate that version string matches semantic versioning format.

    Args:
        version: Version string to validate.

    Returns:
        True if valid, False otherwise.
    """
    return bool(VERSION_PATTERN.fullmatch(version))


def main() -> None:
    """Determine next version using python-semantic-release.

    Delegates bump logic entirely to semantic-release so that Conventional
    Commits drive versioning. This script only:

    - Determines the current version from the latest tag (or 0.1.0 if none)
    - Asks semantic-release for the next version (tries CLI first, then API)
    - Compares current vs next to decide if a bump is needed
    - Prints NEXT_VERSION/NEW_TAG/BUMP_NEEDED for CI consumption
    """
    latest_tag = get_latest_tag()
    if not latest_tag:
        current_version = DEFAULT_VERSION
    else:
        current_version = latest_tag.lstrip("v")

    # Validate current version format
    if not _validate_version_format(current_version):
        print(f"Error: Invalid version format: {current_version}", file=sys.stderr)
        sys.exit(1)

    semantic_version = None
    semantic_release_produced_version = False

    # Try semantic-release CLI first (works on release branches)
    try:
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "semantic_release",
                "version",
                "--print",
                "--no-commit",
                "--no-tag",
                "--no-push",
            ],
            capture_output=True,
            text=True,
            check=False,
        )

        # Check for branch restriction errors (semantic-release exits with code 0 but prints error to stderr)
        error_msg = (result.stderr or "").strip()
        if error_msg and "isn't in any release groups" in error_msg.lower():
            # Branch restriction - fall back to commit analysis
            print("# Branch not in release groups, analyzing commits directly", file=sys.stderr)
            semantic_version = _analyze_commits_with_semantic_release(current_version)
            if semantic_version:
                semantic_release_produced_version = True
        elif result.returncode != 0 and error_msg:
            # Other errors - check if it's a "no version change" scenario
            is_expected_no_bump = any(msg in error_msg.lower() for msg in EXPECTED_NO_BUMP_MESSAGES)
            if not is_expected_no_bump:
                print(f"Error: semantic-release failed: {error_msg}", file=sys.stderr)
                if result.stdout:
                    print(f"stdout: {result.stdout}", file=sys.stderr)
                # Try fallback analysis before exiting
                semantic_version = _analyze_commits_with_semantic_release(current_version)
                if semantic_version:
                    semantic_release_produced_version = True
                else:
                    sys.exit(1)
        else:
            # Success - parse the output
            semantic_version = _parse_semantic_release_output(result.stdout)
            if semantic_version:
                semantic_release_produced_version = True

    except FileNotFoundError:
        print("Error: python-semantic-release not found", file=sys.stderr)
        print("Install it with: pip install python-semantic-release[all]", file=sys.stderr)
        sys.exit(1)
    except Exception as exc:
        print(f"Error running semantic-release: {exc}", file=sys.stderr)
        # Fall back to commit analysis
        semantic_version = _analyze_commits_with_semantic_release(current_version)
        if semantic_version:
            semantic_release_produced_version = True

    # If semantic-release didn't produce a version, it means no bump is needed
    # Use the current version in this case
    if not semantic_version:
        print("# semantic-release did not produce a version (no bump needed)", file=sys.stderr)
        semantic_version = current_version

    # Validate semantic version format
    if not _validate_version_format(semantic_version):
        print(f"Error: Invalid semantic version format: {semantic_version}", file=sys.stderr)
        sys.exit(1)

    # Enforce 0.x semantics: do not allow bumps to 1.0.0+ while still on 0.x.
    try:
        curr_parts = current_version.split(".")
        next_parts = semantic_version.split(".")
        curr_major = int(curr_parts[0])
        curr_minor = int(curr_parts[1])
        next_major = int(next_parts[0])
    except (ValueError, IndexError):
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
    if semantic_release_produced_version:
        print(f"# semantic_release_next={semantic_version}", file=sys.stderr)
    else:
        print(f"# next_version={semantic_version} (using current - no bump needed)", file=sys.stderr)
    print(f"# bump_type={bump_type}", file=sys.stderr)

    if semantic_version == current_version:
        # No semantic bump – either no relevant commits or non-conventional messages.
        next_version = current_version
        new_tag = latest_tag if latest_tag else f"v{DEFAULT_VERSION}"
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
