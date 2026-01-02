#!/usr/bin/env python3
"""Preview version that would be created by CI workflow.

This script uses the same determine_version.py script that CI uses,
ensuring the preview matches exactly what CI will do and also computes a
PEP 440-compatible development preview version for branches.
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


def get_commits_since_tag(tag: str | None) -> list[str]:
    """Get commit messages since the given tag."""
    if tag:
        result = subprocess.run(
            ["git", "log", f"{tag}..HEAD", "--format=%s"],
            capture_output=True,
            text=True,
        )
    else:
        result = subprocess.run(
            ["git", "log", "--format=%s"],
            capture_output=True,
            text=True,
        )

    commits = [c for c in result.stdout.strip().split("\n") if c]
    return commits


def _get_short_sha() -> str:
    """Return short commit SHA for current HEAD."""
    result = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"],
        capture_output=True,
        text=True,
    )
    return result.stdout.strip() or "unknown"


def _get_branch_name() -> str:
    """Return current branch name (or 'detached' if HEAD is detached)."""
    result = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        capture_output=True,
        text=True,
    )
    branch = result.stdout.strip() or "detached"
    return branch


def _sanitize_branch_name(branch: str) -> str:
    """Sanitize branch name for use in local version metadata."""
    return re.sub(r"[^A-Za-z0-9.]+", "-", branch)


def main() -> None:
    """Main function - uses determine_version.py to match CI workflow exactly."""
    latest_tag = get_latest_tag()
    if not latest_tag or latest_tag == "v0.1.0":
        latest_tag = None
        current_version = "0.1.0"
    else:
        current_version = latest_tag.replace("v", "")

    print(f"Latest tag: {latest_tag if latest_tag else 'None'}")
    print(f"Current version: {current_version}")

    commits = get_commits_since_tag(latest_tag)
    commits_count = len(commits)
    print(f"Commits since tag: {commits_count}")

    if commits_count == 0:
        print("Bump type: NONE")
        print("No version bump needed (no commits since tag)")
        print(f"Current version: {current_version}")
        with open("version_preview.txt", "w", encoding="utf-8") as file:
            file.write("BUMP_TYPE=NONE\n")
            file.write("NEXT_VERSION=\n")
            file.write(f"PREVIEW_VERSION={current_version}\n")
        sys.exit(0)

    try:
        result = subprocess.run(
            ["python", "scripts/determine_version.py"],
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            print(f"Error: {result.stderr}", file=sys.stderr)
            sys.exit(1)

        next_version = None
        new_tag = None
        bump_needed: bool | None = None

        for line in result.stdout.strip().split("\n"):
            if line.startswith("NEXT_VERSION="):
                next_version = line.split("=", 1)[1]
            elif line.startswith("NEW_TAG="):
                new_tag = line.split("=", 1)[1]
            elif line.startswith("BUMP_NEEDED="):
                bump_needed = line.split("=", 1)[1] == "true"

        if bump_needed is None or next_version is None:
            print("Error: determine_version.py did not produce expected output", file=sys.stderr)
            sys.exit(1)

        curr_major, curr_minor, curr_patch = (int(x) for x in current_version.split("."))
        next_major, next_minor, next_patch = (int(x) for x in next_version.split("."))

        if next_major > curr_major:
            bump_type = "MAJOR"
        elif next_minor > curr_minor:
            bump_type = "MINOR"
        elif next_patch > curr_patch:
            bump_type = "PATCH"
        else:
            bump_type = "NONE"

        print(f"Bump type: {bump_type}")
        print(f"Next version: {next_version}")
        print(f"New tag: {new_tag}")

        # Compute PEP 440 dev preview version:
        #   <next_version>.dev<commits_count>+g<sha>.branch.<branch>
        short_sha = _get_short_sha()
        branch = _sanitize_branch_name(_get_branch_name())
        preview_version = f"{next_version}.dev{commits_count}+g{short_sha}.branch.{branch}"

        print(f"Preview dev version: {preview_version}")

        with open("version_preview.txt", "w", encoding="utf-8") as file:
            file.write(f"BUMP_TYPE={bump_type}\n")
            file.write(f"NEXT_VERSION={next_version}\n")
            file.write(f"PREVIEW_VERSION={preview_version}\n")

        sys.exit(0)

    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
