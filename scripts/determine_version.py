#!/usr/bin/env python3
"""Thin wrapper around python-semantic-release for CI.

Outputs NEXT_VERSION=, NEW_TAG=, BUMP_NEEDED= for use by tag.yml and build.yml.
Uses semantic-release only; no custom commit parsing or branch heuristics.

Usage:
    python scripts/determine_version.py
"""

from __future__ import annotations

import re
import subprocess
import sys

DEFAULT_VERSION = "0.1.0"
VERSION_RE = re.compile(r"^\d+\.\d+\.\d+$")


def _run(*args: str) -> tuple[int, str, str]:
    r = subprocess.run(
        [sys.executable, "-m", "semantic_release", "version", *args],
        capture_output=True,
        text=True,
        timeout=60,
    )
    return r.returncode, (r.stdout or "").strip(), (r.stderr or "").strip()


def _parse_version(s: str) -> str | None:
    for line in s.strip().split("\n"):
        candidate = line.strip()
        if VERSION_RE.fullmatch(candidate):
            return candidate
    return None


def main() -> None:
    code, out, err = _run("--print")
    no_release = "isn't in any release groups" in err or "no release" in err.lower()

    if code != 0 or no_release or not _parse_version(out):
        _, last_out, _ = _run("--print-last-released")
        current = _parse_version(last_out) or DEFAULT_VERSION
        next_version = current
        new_tag = f"v{current}" if not current.startswith("v") else current
        bump_needed = "false"
    else:
        next_version = _parse_version(out)
        assert next_version
        _, tag_out, _ = _run("--print-tag")
        t = tag_out.strip()
        new_tag = t if t.startswith("v") else f"v{next_version}"
        _, last_out, _ = _run("--print-last-released")
        current = _parse_version(last_out) or DEFAULT_VERSION
        bump_needed = "true" if next_version != current else "false"

    print(f"NEXT_VERSION={next_version}")
    print(f"NEW_TAG={new_tag}")
    print(f"BUMP_NEEDED={bump_needed}")


if __name__ == "__main__":
    main()
