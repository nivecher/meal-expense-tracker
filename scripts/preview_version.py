#!/usr/bin/env python3
"""Preview version that would be created by CI workflow.

This script uses the same determine_version.py script that CI uses,
ensuring the preview matches exactly what CI will do.
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


def main():
    """Main function - uses determine_version.py to match CI workflow exactly."""
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
    commits_count = len(commits)
    print(f"Commits since tag: {commits_count}")

    if commits_count == 0:
        print("Bump type: NONE")
        print("No version bump needed (no commits since tag)")
        print(f"Current version: {current_version}")
        with open("version_preview.txt", "w") as f:
            f.write("BUMP_TYPE=NONE\n")
            f.write("NEXT_VERSION=\n")
        sys.exit(0)

    # Use the same script that CI uses
    try:
        result = subprocess.run(
            ["python", "scripts/determine_version.py"],
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            print(f"Error: {result.stderr}", file=sys.stderr)
            sys.exit(1)

        # Parse output from determine_version.py
        next_version = None
        new_tag = None
        bump_needed = None

        for line in result.stdout.strip().split("\n"):
            if line.startswith("NEXT_VERSION="):
                next_version = line.split("=", 1)[1]
            elif line.startswith("NEW_TAG="):
                new_tag = line.split("=", 1)[1]
            elif line.startswith("BUMP_NEEDED="):
                bump_needed = line.split("=", 1)[1] == "true"

        if bump_needed and next_version:
            # Determine bump type
            curr_parts = current_version.split(".")
            next_parts = next_version.split(".")

            if int(next_parts[0]) > int(curr_parts[0]):
                bump_type = "MAJOR"
            elif int(next_parts[1]) > int(curr_parts[1]):
                bump_type = "MINOR"
            elif int(next_parts[2]) > int(curr_parts[2]):
                bump_type = "PATCH"
            else:
                bump_type = "NONE"

            print(f"Bump type: {bump_type}")
            print(f"Next version: {next_version}")
            print(f"New tag: {new_tag}")

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

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
