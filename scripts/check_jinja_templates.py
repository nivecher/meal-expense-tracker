#!/usr/bin/env python3
"""Compile Jinja templates to catch syntax errors in app/templates."""

from __future__ import annotations

import sys
from pathlib import Path

from jinja2 import Environment, TemplateSyntaxError


def main() -> int:
    repo_root = Path(__file__).resolve().parent.parent
    template_root = repo_root / "app" / "templates"

    env = Environment()
    failures = 0

    for template_path in sorted(template_root.rglob("*.html")):
        relative_path = template_path.relative_to(template_root).as_posix()
        try:
            env.parse(template_path.read_text(encoding="utf-8"))
        except TemplateSyntaxError as exc:
            failures += 1
            print(f"{template_path}:{exc.lineno}: {exc.message}", file=sys.stderr)

    if failures:
        print(f"Jinja template syntax check failed for {failures} template(s).", file=sys.stderr)
        return 1

    print("Jinja template syntax OK.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
