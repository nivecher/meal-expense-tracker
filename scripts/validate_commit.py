import sys
import re


def validate_commit_message(message: str) -> None:
    """Validate commit message format.

    Format: <type>(<scope>): <description>

    Types:
    - feat: A new feature
    - fix: A bug fix
    - docs: Documentation changes
    - style: Code style changes (formatting, etc.)
    - refactor: Code refactoring
    - perf: Performance improvements
    - test: Adding missing tests
    - chore: Changes to build process or auxiliary tools
    - ci: Changes to CI configuration files
    - build: Changes that affect the build system or external dependencies
    """

    # Check for empty message
    if not message.strip():
        print("Error: Commit message cannot be empty")
        sys.exit(1)

    # Split message into lines
    lines = message.split("\n")
    first_line = lines[0].strip()

    # Check first line format
    pattern = (
        r"^("
        + "|".join(
            [
                "feat",
                "fix",
                "docs",
                "style",
                "refactor",
                "perf",
                "test",
                "chore",
                "ci",
                "build",
            ]
        )
        + r")\(([^)]+)\):\s+(.+)"
    )
    if not re.match(pattern, first_line):
        print("Error: Invalid commit message format")
        print("Expected format: <type>(<scope>): <description>")
        print("Available types:")
        print("feat, fix, docs, style, refactor, perf, test, chore, ci, build")
        sys.exit(1)

    # Check for breaking change
    if any(line.strip().startswith("BREAKING CHANGE:") for line in lines):
        print("Warning: This commit contains a breaking change")

    print("Commit message format is valid")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python validate_commit.py <commit-message>")
        sys.exit(1)

    message = sys.argv[1]
    validate_commit_message(message)
