import subprocess
import re
from pathlib import Path
import toml


def get_latest_git_tag():
    """Get the latest git tag."""
    try:
        # Get all tags sorted by version
        tags = (
            subprocess.check_output(["git", "tag", "-l"]).decode("utf-8").splitlines()
        )
        # Filter out invalid tags (like vv0.1.1)
        tags = [tag for tag in tags if re.match(r"^v\d+\.\d+\.\d+$", tag)]
        # Sort by version
        tags.sort(key=lambda x: tuple(map(int, x[1:].split("."))))
        return tags[-1] if tags else None
    except subprocess.CalledProcessError:
        return None


def update_pyproject_version(version):
    """Update version in pyproject.toml."""
    pyproject_path = Path("pyproject.toml")
    if not pyproject_path.exists():
        print("Error: pyproject.toml not found")
        return False

    # Read current pyproject.toml
    pyproject = toml.load(pyproject_path)

    # Update version in project section
    pyproject["project"]["version"] = version

    # Update version in tool section for mypy
    pyproject["tool"]["mypy"]["python_version"] = version.split(".")[0]

    # Write back to file
    with open(pyproject_path, "w") as f:
        toml.dump(pyproject, f)

    return True


def main():
    latest_tag = get_latest_git_tag()
    if not latest_tag:
        print("No valid git tags found")
        return

    # Remove 'v' prefix if present
    version = latest_tag[1:] if latest_tag.startswith("v") else latest_tag

    # Check if version is already up to date
    pyproject_path = Path("pyproject.toml")
    if pyproject_path.exists():
        pyproject = toml.load(pyproject_path)
        current_version = pyproject["project"]["version"]
        if current_version == version:
            print(f"Version {version} is already up to date")
            return

    if update_pyproject_version(version):
        print("Version updated successfully")
        return 0
    else:
        print("Failed to update version")
        return 1


if __name__ == "__main__":
    main()
