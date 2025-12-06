#!/usr/bin/env python3
"""Preview version that would be created by CI workflow.

This script analyzes git commits to determine what version bump would occur
based on conventional commit messages, matching the logic used by python-semantic-release.
"""

import os
import re
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


def get_commits_since_tag(tag):
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


def analyze_commits(commits):
    """Analyze commits to determine version bump type."""
    feat_count = sum(1 for c in commits if re.match(r"^feat(!)?:", c, re.IGNORECASE))
    fix_count = sum(1 for c in commits if re.match(r"^fix(!)?:", c, re.IGNORECASE))
    breaking_count = sum(1 for c in commits if "BREAKING CHANGE" in c or re.match(r"^feat!|^fix!", c, re.IGNORECASE))

    return feat_count, fix_count, breaking_count


def calculate_next_version(current_version, feat_count, fix_count, breaking_count):
    """Calculate next version based on commit analysis."""
    parts = current_version.split(".")
    major = int(parts[0]) if len(parts) > 0 else 0
    minor = int(parts[1]) if len(parts) > 1 else 0
    patch = int(parts[2]) if len(parts) > 2 else 0

    if breaking_count > 0:
        major += 1
        minor = 0
        patch = 0
        bump_type = "MAJOR"
    elif feat_count > 0:
        minor += 1
        patch = 0
        bump_type = "MINOR"
    elif fix_count > 0:
        patch += 1
        bump_type = "PATCH"
    else:
        bump_type = "NONE"

    next_version = f"{major}.{minor}.{patch}" if bump_type != "NONE" else None
    return next_version, bump_type


def main():
    """Main function."""
    # Get latest tag
    latest_tag = get_latest_tag()
    if not latest_tag or latest_tag == "v0.1.0":
        latest_tag = None
        current_version = "0.1.0"
    else:
        current_version = latest_tag.replace("v", "")

    print(f"Latest tag: {latest_tag if latest_tag else 'None'}")
    print(f"Current version: {current_version}")

    # Get commits since tag
    commits = get_commits_since_tag(latest_tag)
    print(f"Commits since tag: {len(commits)}")

    # Analyze commits
    feat_count, fix_count, breaking_count = analyze_commits(commits)
    print(f"feat: {feat_count}, fix: {fix_count}, breaking: {breaking_count}")

    # Calculate next version
    next_version, bump_type = calculate_next_version(
        current_version,
        feat_count,
        fix_count,
        breaking_count,
    )

    # Output results
    if next_version:
        print(f"Bump type: {bump_type}")
        print(f"Next version: {next_version}")
        print(f"New tag: v{next_version}")
        # Write to file for Makefile to read
        with open("version_preview.txt", "w") as f:
            f.write(f"BUMP_TYPE={bump_type}\n")
            f.write(f"NEXT_VERSION={next_version}\n")
        sys.exit(0)
    else:
        print("Bump type: NONE")
        print("No version bump needed")
        print(f"Current version: {current_version}")
        with open("version_preview.txt", "w") as f:
            f.write("BUMP_TYPE=NONE\n")
            f.write("NEXT_VERSION=\n")
        sys.exit(0)


if __name__ == "__main__":
    main()
