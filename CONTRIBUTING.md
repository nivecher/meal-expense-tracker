# Contributing Guide

Thank you for considering contributing to Meal Expense Tracker!

## Development workflow

- Create a feature branch from `main`.
- Make small, focused edits aligned with TIGER principles.
- Write/adjust tests to cover changes (80%+ coverage).
- Run formatters/linters/tests locally before opening a PR.

## Checks to run locally

```bash
make format
make lint
make test
npm run lint:js
pre-commit run -a
```

## Coding standards

- Python: Black (120 cols), isort, flake8, mypy strict; CSRF enabled for forms.
- JS: ESLint v9 flat config (`eslint.config.js`), single quotes, semicolons.
- Docs/Markdown: markdownlint; prefer updating `README.md`/docs for behavior changes.

## Commit messages

- Use present tense, short imperative subject (<50 chars), and body for rationale where useful.

## Pull requests

- Keep PRs small and focused; include before/after context and any new env vars/migrations.
