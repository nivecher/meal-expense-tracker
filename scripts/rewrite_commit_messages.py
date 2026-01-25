#!/usr/bin/env python3
"""Rewrite commit messages to Conventional Commits format.

Used with git filter-branch --msg-filter to normalize existing history.
"""

from __future__ import annotations

import re
import sys

CONVENTIONAL_RE = re.compile(r"^(?P<type>[a-z]+)(?:\((?P<scope>[^)]+)\))?: (?P<subject>.+)$")


def _detect_type(subject: str) -> str:
    lowered = subject.lower()
    if lowered.startswith(("add ", "added ", "introduce ", "introduced ")):
        return "feat"
    if lowered.startswith(("fix ", "fixed ")):
        return "fix"
    if lowered.startswith("refactor "):
        return "refactor"
    if lowered.startswith(("remove ", "removed ", "delete ", "deleted ")):
        return "chore"
    if lowered.startswith(("update ", "updated ")):
        return "chore"
    if "workflow" in lowered or "ci" in lowered:
        return "ci"
    if "readme" in lowered or "doc" in lowered:
        return "docs"
    if "test" in lowered:
        return "test"
    return "chore"


def _sentence_case(subject: str) -> str:
    if not subject:
        return subject
    trimmed = subject.strip()
    if trimmed.endswith("."):
        trimmed = trimmed[:-1]
    lowered = trimmed.lower()
    return lowered[:1].upper() + lowered[1:]


def main() -> int:
    message = sys.stdin.read()
    if not message:
        return 0

    lines = message.splitlines()
    subject = lines[0].strip()

    if subject.startswith("Merge "):
        sys.stdout.write(message)
        return 0

    match = CONVENTIONAL_RE.match(subject)
    if match:
        commit_type = match.group("type")
        scope = match.group("scope")
        subject = match.group("subject")
        new_subject = _sentence_case(subject)
        scope_part = f"({scope})" if scope else ""
        sys.stdout.write(f"{commit_type}{scope_part}: {new_subject}\n")

        if len(lines) > 1:
            body = "\n".join(lines[1:]).rstrip()
            if body:
                sys.stdout.write("\n")
                sys.stdout.write(body)
                sys.stdout.write("\n")
        return 0

    commit_type = _detect_type(subject)
    new_subject = _sentence_case(subject)
    sys.stdout.write(f"{commit_type}: {new_subject}\n")

    if len(lines) > 1:
        body = "\n".join(lines[1:]).rstrip()
        if body:
            sys.stdout.write("\n")
            sys.stdout.write(body)
            sys.stdout.write("\n")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
