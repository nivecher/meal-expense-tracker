# Contributing Guide

Thank you for considering contributing to Meal Expense Tracker!

## Development workflow

- Create a feature branch from `main`.
- Make small, focused edits aligned with TIGER principles.
- Write/adjust tests to cover changes (80%+ coverage).
- Run formatters/linters/tests locally before opening a PR.

## VSCode Setup

For the best development experience, we recommend using VSCode with the recommended extensions.

### Installing Recommended Extensions

1. Open the project in VSCode
2. When prompted, click "Install" to install all recommended extensions
3. Alternatively, open the Command Palette (Ctrl+Shift+P / Cmd+Shift+P) and run "Extensions: Show Recommended Extensions"

### Required Extensions

The following extensions are recommended for this project:

- **Python**: `ms-python.python` - Python language support
- **Black Formatter**: `ms-python.black-formatter` - Python code formatting
- **Ruff**: `charliermarsh.ruff` - Python linting (replaces Flake8)
- **ESLint**: `dbaeumer.vscode-eslint` - JavaScript linting
- **Prettier**: `esbenp.prettier-vscode` - Code formatting (HTML, CSS, Markdown, JSON, YAML)
- **Stylelint**: `stylelint.vscode-stylelint` - CSS linting
- **Markdownlint**: `davidanson.vscode-markdownlint` - Markdown linting
- **YAML**: `redhat.vscode-yaml` - YAML support
- **Terraform**: `hashicorp.terraform` - Terraform support

### VSCode Settings

The project includes workspace settings (`.vscode/settings.json`) that configure:

- Formatters for each file type
- Format on save
- Linter enablement
- Configuration file paths

These settings are automatically applied when you open the workspace.

### Troubleshooting VSCode Extensions

If linting or formatting doesn't work in VSCode:

1. **Check extensions are installed**: Open Extensions view (Ctrl+Shift+X) and verify all recommended extensions are installed
2. **Reload window**: Press Ctrl+Shift+P and run "Developer: Reload Window"
3. **Check output**: Open Output panel (View → Output) and select the linter/formatter to see error messages
4. **Verify Python environment**: Ensure your Python interpreter is selected (Ctrl+Shift+P → "Python: Select Interpreter")
5. **Check npm dependencies**: Run `npm install` to ensure Node.js dependencies are installed

## Checks to run locally

### Quick Check (Recommended)

```bash
make format    # Format all code
make lint      # Run all linters
make test      # Run all tests
```

### Comprehensive Check

```bash
make format              # Format all code
make lint                # Run all linters (Python, HTML, CSS, JS, Markdown, YAML, JSON, TOML, Terraform)
make test                # Run all tests
pre-commit run --all-files  # Run all pre-commit hooks
make validate-linting-sync  # Validate linting tool synchronization
```

### Individual Language Checks

```bash
# Python
make lint-python
make format-python

# JavaScript
make lint-js
make format-js

# HTML
make lint-html
make format-html

# CSS
make lint-css
make format-css

# Markdown
make lint-markdown

# YAML/JSON/TOML
make lint-yaml
make lint-json
make lint-toml

# Terraform
make lint-terraform-fmt
make tf-validate
```

### Pre-commit Hooks

Pre-commit hooks automatically run on `git commit`. To run them manually:

```bash
pre-commit run --all-files
```

To install pre-commit hooks (one-time setup):

```bash
pre-commit install
```

## Coding standards

### Python

- **Formatter**: Black (120 char line length, Python 3.13 target)
- **Linter**: Ruff (max complexity 10, configured in `pyproject.toml`)
  - Replaces Flake8 (linting), isort (import sorting), and autoflake (unused imports)
- **Type checking**: Mypy (configured but not actively enforced)
- **Security**: Bandit (configured in `.bandit`)
- **CSRF**: Enabled for all forms

### JavaScript

- **Linter/Formatter**: ESLint 9.34.0 (flat config in `eslint.config.js`)
- **Style**: Single quotes, semicolons, camelCase
- **Config**: See `eslint.config.js` for complete rules

### HTML

- **Formatter**: Prettier (configured in `.prettierrc`)
- **Style**: 4-space indent, double quotes

### CSS

- **Linter**: Stylelint 16.24.0 (configured in `.stylelintrc.json`)
- **Formatter**: Stylelint with auto-fix

### Markdown

- **Linter**: markdownlint-cli v0.38.0 (configured in `.markdownlint.json`)
- **Formatter**: Prettier (80 char line length for prose)

### YAML/JSON/TOML

- **Validation**: Pre-commit hooks (check-yaml, check-json, check-toml)
- **Formatter**: Prettier (for YAML/JSON)

### Terraform

- **Formatter**: terraform fmt
- **Validator**: terraform validate

For detailed linting standards, see [docs/LINTING_STANDARDS.md](docs/LINTING_STANDARDS.md).

## Linting Workflow

### Before Committing

1. **Format code**: `make format`
2. **Run linters**: `make lint`
3. **Fix issues**: Address any linting errors
4. **Run tests**: `make test`
5. **Validate sync**: `make validate-linting-sync` (optional, checks tool versions)

### In VSCode

With the recommended extensions installed:

- Code is automatically formatted on save
- Linting errors are shown inline
- Quick fixes are available via lightbulb icon (Ctrl+.)

### Automated Pre-commit Checks

Pre-commit hooks automatically:

- Format Python code (Black, Ruff for imports/unused code)
- Lint Python code (Ruff, Bandit)
- Lint JavaScript (ESLint)
- Lint HTML/CSS (Prettier, Stylelint)
- Lint Markdown (markdownlint, Prettier)
- Validate YAML/JSON/TOML
- Format Terraform files

If hooks fail, fix the issues and commit again.

### CI/CD

GitHub Actions runs the same linting checks:

- All linters run automatically on push/PR
- Same tools and versions as local development
- Failures block merging

## Commit messages

- Use present tense, short imperative subject (<50 chars), and body for rationale where useful.
- Examples:
  - `Add expense filtering by date range`
  - `Fix restaurant search autocomplete`
  - `Update dependencies to latest versions`

## Pull requests

- Keep PRs small and focused; include before/after context and any new env vars/migrations.
- Ensure all linting checks pass before requesting review
- Include relevant tests for new features
- Update documentation if behavior changes

## Troubleshooting

### Linting Issues

**Problem**: Linter not running in VSCode

- **Solution**: Check extensions are installed and reload window

**Problem**: Pre-commit hooks failing

- **Solution**: Run `pre-commit run --all-files` to see detailed errors

**Problem**: Version mismatches

- **Solution**: Run `make validate-linting-sync` to identify discrepancies

**Problem**: Make targets failing

- **Solution**: Ensure virtual environment is activated and dependencies installed

### Common Fixes

```bash
# Reinstall dependencies
pip install -r requirements-dev.txt
npm install

# Reinstall pre-commit hooks
pre-commit uninstall
pre-commit install

# Clear caches
rm -rf .pytest_cache .mypy_cache __pycache__
```
