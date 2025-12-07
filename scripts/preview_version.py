#!/usr/bin/env python3
"""Preview next version tag that would be created by CI workflow.

This script uses python-semantic-release to determine the exact next version
that would be created based on conventional commits, matching the CI workflow logic.
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
    """Main function - uses python-semantic-release to determine next version.

    This matches exactly what the CI workflow does - uses semantic-release
    to analyze conventional commits and determine the next version tag.
    """
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

    # Use python-semantic-release to determine next version (matches CI workflow)
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
            # Look for version pattern (e.g., "1.2.3")
            import re

            version_match = re.search(r"^(\d+\.\d+\.\d+)$", line.strip())
            if version_match:
                semantic_version = version_match.group(1)
                break

        # Validate semantic-release suggestion (matches CI workflow validation)
        if semantic_version and semantic_version != current_version:
            curr_parts = current_version.split(".")
            next_parts = semantic_version.split(".")

            # Validate: prevent invalid jumps (e.g., 0.6.0 -> 1.0.0 unless breaking change)
            if curr_parts[0] == "0" and next_parts[0] == "1":
                # Invalid: jumping from 0.x.x to 1.0.0 (should be 0.x+1.0 or 0.x.y+1)
                print(f"⚠️  Semantic-release suggested invalid jump from {current_version} to {semantic_version}")
                print("   Ignoring and using fallback patch bump")
                semantic_version = None
            elif int(next_parts[0]) > int(curr_parts[0]) + 1:
                # Invalid: major version jumped by more than 1
                print("⚠️  Semantic-release suggested invalid major jump")
                print("   Ignoring and using fallback patch bump")
                semantic_version = None

        if semantic_version and semantic_version != current_version:
            # Valid semantic-release suggestion
            curr_parts = current_version.split(".")
            next_parts = semantic_version.split(".")

            if int(next_parts[0]) > int(curr_parts[0]):
                bump_type = "MAJOR"
            elif int(next_parts[1]) > int(curr_parts[1]):
                bump_type = "MINOR"
            elif int(next_parts[2]) > int(curr_parts[2]):
                bump_type = "PATCH"
            else:
                bump_type = "NONE"

            print(f"Bump type: {bump_type}")
            print(f"Next version: {semantic_version}")
            print(f"New tag: v{semantic_version}")

            with open("version_preview.txt", "w") as f:
                f.write(f"BUMP_TYPE={bump_type}\n")
                f.write(f"NEXT_VERSION={semantic_version}\n")
            sys.exit(0)
        else:
            # No valid semantic bump detected - use fallback patch bump (matches CI workflow)
            if commits_count > 0:
                # Fallback: do a patch bump if commits exist
                curr_parts = current_version.split(".")
                major = int(curr_parts[0])
                minor = int(curr_parts[1])
                patch = int(curr_parts[2]) + 1
                fallback_version = f"{major}.{minor}.{patch}"

                print("Bump type: PATCH (fallback)")
                print(f"Next version: {fallback_version}")
                print(f"New tag: v{fallback_version}")
                print("   (semantic-release didn't detect a bump, using patch bump fallback)")

                with open("version_preview.txt", "w") as f:
                    f.write("BUMP_TYPE=PATCH\n")
                    f.write(f"NEXT_VERSION={fallback_version}\n")
                sys.exit(0)
            else:
                # No commits, no bump
                print("Bump type: NONE")
                print("No version bump needed (no commits since tag)")
                print(f"Current version: {current_version}")
                with open("version_preview.txt", "w") as f:
                    f.write("BUMP_TYPE=NONE\n")
                    f.write("NEXT_VERSION=\n")
                sys.exit(0)

    except FileNotFoundError:
        print("Error: python-semantic-release not found", file=sys.stderr)
        print("Install it with: pip install python-semantic-release[all]", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error running semantic-release: {e}", file=sys.stderr)
        print("Falling back to simple analysis...", file=sys.stderr)
        # Fallback to simple analysis if semantic-release fails
        print("Bump type: UNKNOWN")
        print("Could not determine version using semantic-release")
        with open("version_preview.txt", "w") as f:
            f.write("BUMP_TYPE=UNKNOWN\n")
            f.write("NEXT_VERSION=\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
