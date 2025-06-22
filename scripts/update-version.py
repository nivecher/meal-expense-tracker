import subprocess
import re
from pathlib import Path
import toml


def get_latest_git_tag():
    """Get the latest git tag."""
    try:
        # Get all tags sorted by version
        tags = subprocess.check_output(["git", "tag", "-l"]).decode("utf-8").splitlines()
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

    # Update Python version in mypy configuration
    if "tool" in pyproject and "mypy" in pyproject["tool"]:
        pyproject["tool"]["mypy"]["python_version"] = ".".join(version.split(".")[:2])

    # Write back to file
    with open(pyproject_path, "w") as f:
        toml.dump(pyproject, f)

    # Update the version file that setuptools_scm writes to
    version_file = Path("app/_version.py")
    version_file.parent.mkdir(parents=True, exist_ok=True)
    version_file.write_text(f'__version__ = "{version}"\n')

    return True


def get_current_version():
    """Get current version from _version.py or return None if not set."""
    version_file = Path("app/_version.py")
    if not version_file.exists():
        return None

    # Simple regex to extract version from _version.py
    content = version_file.read_text()
    match = re.search(r'__version__\s*=\s*["\']([^"\']+)["\']', content)
    return match.group(1) if match else None


def main():
    latest_tag = get_latest_git_tag()
    if not latest_tag:
        print("No valid git tags found")
        return 1

    # Remove 'v' prefix if present
    version = latest_tag[1:] if latest_tag.startswith("v") else latest_tag

    # Get current version from _version.py
    current_version = get_current_version()

    if current_version == version:
        print(f"Version {version} is already up to date")
        return 0

    if update_pyproject_version(version):
        print(f"Version updated to {version}")
        return 0
    else:
        print("Failed to update version")
        return 1


if __name__ == "__main__":
    main()
