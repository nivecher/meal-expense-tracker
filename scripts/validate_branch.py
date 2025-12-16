#!/usr/bin/env python3
"""Validate branch name format.

Branch names must follow: <type>/<description>
Where type is one of: feat, fix, docs, style, refactor, test, chore, ci, perf, revert, wip
And description is kebab-case (lowercase with hyphens).
"""

import re
import sys


def validate_branch_name(branch_name: str) -> None:
    """Validate branch name format.

    Format: <type>/<description>

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
    - revert: Revert a previous commit
    - wip: Work in progress

    Protected branches (main, develop) are allowed without validation.
    """
    # Protected branches are always allowed
    protected_branches = ["main", "develop", "master"]
    if branch_name in protected_branches:
        print(f"Branch '{branch_name}' is a protected branch (allowed)")
        return

    # Check for empty name
    if not branch_name.strip():
        print("Error: Branch name cannot be empty")
        sys.exit(1)

    # Remove 'refs/heads/' prefix if present (from git hooks)
    branch_name = branch_name.replace("refs/heads/", "")

    # Check format: <type>/<description>
    allowed_types = [
        "feat",
        "fix",
        "docs",
        "style",
        "refactor",
        "perf",
        "test",
        "chore",
        "ci",
        "revert",
        "wip",
    ]

    # Pattern: type/description where description is kebab-case
    pattern = r"^(" + "|".join(allowed_types) + r")/([a-z0-9]+(?:-[a-z0-9]+)*)$"

    if not re.match(pattern, branch_name):
        print("Error: Invalid branch name format")
        print(f"Branch name: {branch_name}")
        print("Expected format: <type>/<description>")
        print("Available types:")
        print(", ".join(allowed_types))
        print("\nExamples:")
        print("  feat/add-expense-filtering")
        print("  fix/restaurant-search-bug")
        print("  docs/update-api-documentation")
        print("\nDescription must be:")
        print("  - Lowercase letters and numbers only")
        print("  - Hyphens allowed (kebab-case)")
        print("  - No spaces or special characters")
        sys.exit(1)

    print(f"Branch name '{branch_name}' is valid")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python validate_branch.py <branch-name>")
        print("\nExample:")
        print("  python validate_branch.py feat/add-expense-filtering")
        sys.exit(1)

    branch_name = sys.argv[1]
    validate_branch_name(branch_name)
