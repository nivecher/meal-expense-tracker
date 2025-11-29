# Linting Standards Documentation

## Overview

This document defines the linting and formatting standards for the Meal Expense Tracker project. All linting tools must be configured consistently across four environments:

1. **VSCode** (IDE plugins)
2. **Make** (local development)
3. **pre-commit** (git hooks)
4. **GitHub Actions** (CI/CD)

## Standardization Principles

1. **Config Files Over Arguments**: Prefer configuration files (pyproject.toml, etc.) over explicit command-line arguments for consistency
2. **Version Pinning**: All tool versions must be pinned and consistent across environments
3. **Comprehensive Coverage**: All languages should be linted in all applicable environments
4. **Validation**: Automated validation ensures all environments stay in sync

## Language Coverage

- Python
- JavaScript
- HTML
- CSS
- Markdown
- YAML/JSON/TOML
- Terraform (HCL)

## Tool Versions

### Python Tools

- **Black**: 24.10.0 (code formatting)
- **Ruff**: 0.8.0+ (linting, import sorting, unused code removal - replaces Flake8, isort, autoflake)
- **Bandit**: 1.8.6 (security linting)
- **Mypy**: 1.13.0 (type checking - enabled in pre-commit and Makefile)

### JavaScript/Web Tools

- **ESLint**: 9.34.0
- **Prettier**: 3.3.3
- **Stylelint**: 16.24.0
- **markdownlint-cli**: v0.38.0

### Infrastructure Tools

- **Terraform**: 1.13.5
- **pre-commit-hooks**: v6.0.0

## Detailed Tool Configuration

### Python Linting

#### Black (24.10.0)

**Purpose**: Code formatting

**Configuration File**: `pyproject.toml`

```toml
[tool.black]
line-length = 120
target-version = ["py313"]
include = "\\.pyi?$"
```

**Standard Command**:

- **Lint (check)**: `black --check app tests`
- **Format**: `black app/ tests/ migrations/`

**Environment Usage**:

- **VSCode**: Extension: `ms-python.black-formatter`
- **Make**: `black --check app tests` (lint), `black app/ tests/ migrations/` (format)
- **Pre-commit**: `black` (uses pyproject.toml config)
- **GitHub Actions**: Via `make lint`

**Notes**: All environments rely on `pyproject.toml` configuration. No explicit arguments needed.

#### Ruff (0.8.0+)

**Purpose**: Fast Python linter and formatter that replaces Flake8, isort, and autoflake

**Configuration File**: `pyproject.toml`

```toml
[tool.ruff]
line-length = 120
target-version = "py313"

[tool.ruff.lint]
select = ["E", "W", "F", "I", "B", "C4", "UP", "PTH"]
extend-select = ["PTH"]
ignore = [
    "E203", "E266", "E501", "E402", "E712", "E721", "E722",
    "E741", "E742", "E743", "W292", "F401", "F403", "F405",
    "F811", "B011", "B014", "B019", "B007", "B905", "B904",
    "C416", "UP035", "UP047", "UP040", "UP007",
    "PTH100", "PTH110", "PTH118", "PTH120", "PTH112",
    "PTH103", "PTH107", "PTH122", "PTH123",
]

[tool.ruff.lint.per-file-ignores]
"__init__.py" = ["F401"]
"scripts/*.py" = ["T201", "PTH110", "PTH118", "PTH120"]
"tests/*.py" = ["E501", "E402", "ARG001", "ARG002", "ARG003", "F841", "F403", "F405", "PTH110", "PTH118", "PTH120", "PTH112", "PTH103", "PTH107", "PTH122", "B017"]

[tool.ruff.lint.mccabe]
max-complexity = 10

[tool.ruff.lint.isort]
known-first-party = ["app"]
combine-as-imports = true
split-on-trailing-comma = true
force-sort-within-sections = true
```

**Standard Commands**:

- **Lint (check)**: `ruff check app tests`
- **Lint with auto-fix**: `ruff check --fix app tests`
- **Format**: `ruff format app tests` (Note: Currently using Black for formatting in Phase 1)

**Environment Usage**:

- **VSCode**: Extension: `charliermarsh.ruff` (recommended)
- **Make**: `ruff check app tests` (lint), `ruff check --fix app tests` (format imports/unused code)
- **Pre-commit**: `ruff` hook with `--fix --exit-non-zero-on-fix` (uses pyproject.toml config)
- **GitHub Actions**: Via `make lint`

**Notes**:

- Ruff replaces Flake8 (linting), isort (import sorting), and autoflake (unused code removal)
- All environments rely on `pyproject.toml` configuration
- Ruff is 10-100x faster than the tools it replaces
- Black is still used for code formatting in Phase 1; Ruff formatter will be evaluated in Phase 2

#### Bandit (1.8.6)

**Purpose**: Security vulnerability scanning

**Configuration File**: `.bandit`

```yaml
targets: .
recursive: true
skips:
  - B404 # import_subprocess - subprocess module is needed for secret rotation
  - B603 # subprocess_without_shell_equals_true - shell=False is used
  - B105 # hardcoded_password_string - These are just user messages, not actual passwords
```

**Standard Command**: `bandit -c .bandit -r app/`

**Environment Usage**:

- **VSCode**: Not configured
- **Make**: `bandit -c .bandit -r app/` (via `make security-bandit`)
- **Pre-commit**: `bandit -c .bandit -r` (files: ^app/, exclude: (tests/|venv/|.venv/|migrations/))
- **GitHub Actions**: Via `make security-check`

**Notes**: All environments use `.bandit` configuration file.

#### Mypy (1.13.0)

**Purpose**: Static type checking

**Configuration File**: `pyproject.toml`

```toml
[tool.mypy]
python_version = "3.13"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
disallow_incomplete_defs = true
check_untyped_defs = true
disallow_untyped_decorators = true
no_implicit_optional = true
warn_redundant_casts = true
warn_unused_ignores = true
warn_no_return = true
warn_unreachable = true
```

**Standard Command**: `mypy app --config-file=pyproject.toml`

**Environment Usage**:

- **VSCode**: Extension: `ms-python.mypy-type-checker`
- **Make**: `mypy app --config-file=pyproject.toml` (via `make lint-mypy`)
- **Pre-commit**: `mypy` (uses pyproject.toml config, files: ^app/.\*\.py$)
- **GitHub Actions**: Via `make lint` (includes lint-mypy)

**Notes**: All environments rely on `pyproject.toml` configuration. Excludes tests, migrations, and scripts.

### JavaScript Linting

#### ESLint (9.34.0)

**Purpose**: JavaScript linting

**Configuration File**: `eslint.config.js`

**Standard Command**: `eslint --config eslint.config.js "app/static/js/**/*.js"`

**Environment Usage**:

- **VSCode**: Extension: `dbaeumer.vscode-eslint`
- **Make**: `npm run lint:js` → `eslint --config eslint.config.js "app/static/js/**/*.js"`
- **Pre-commit**: Local hook → `npm run lint:js`
- **GitHub Actions**: Via `make lint`

**Notes**: All environments use the same npm script for consistency.

#### Prettier for JavaScript (3.3.3)

**Purpose**: JavaScript formatting

**Configuration File**: `.prettierrc`

**Standard Command**: `eslint --config eslint.config.js "app/static/js/**/*.js" --fix`

**Environment Usage**:

- **VSCode**: Extension: `esbenp.prettier-vscode` (configured to use ESLint for JS)
- **Make**: `npm run format:js` → `eslint --config eslint.config.js "app/static/js/**/*.js" --fix`
- **Pre-commit**: Not configured (ESLint handles formatting)
- **GitHub Actions**: Via `make format`

**Notes**: ESLint is used for both linting and formatting JavaScript.

### HTML Linting

#### Prettier (3.3.3)

**Purpose**: HTML template formatting

**Configuration File**: `.prettierrc`

```json
{
  "overrides": [
    {
      "files": ["*.html", "*.jinja", "*.j2"],
      "options": {
        "parser": "html",
        "htmlWhitespaceSensitivity": "strict",
        "printWidth": 120,
        "tabWidth": 4,
        "bracketSameLine": true,
        "singleAttributePerLine": false,
        "singleQuote": false
      }
    }
  ]
}
```

**Standard Command**: `prettier --check "app/templates/**/*.html"`

**Environment Usage**:

- **VSCode**: Extension: `esbenp.prettier-vscode`
- **Make**: `npm run lint-html` → `prettier --check "app/templates/**/*.html"`
- **Pre-commit**: Local hook → `npm run lint-html`
- **GitHub Actions**: Via `make lint`

**Notes**: All environments use the same npm script.

### CSS Linting

#### Stylelint (16.24.0)

**Purpose**: CSS linting

**Configuration File**: `.stylelintrc.json`

**Standard Command**: `stylelint --config .stylelintrc.json "app/static/css/**/*.css"`

**Environment Usage**:

- **VSCode**: Extension: `stylelint.vscode-stylelint`
- **Make**: `npm run lint:css` → `stylelint --config .stylelintrc.json "app/static/css/**/*.css"`
- **Pre-commit**: Local hook → `npm run lint:css`
- **GitHub Actions**: Via `make lint`

**Notes**: All environments use the same npm script.

### Markdown Linting

#### markdownlint-cli (v0.38.0)

**Purpose**: Markdown linting

**Configuration File**: `.markdownlint.json`

**Standard Command**: `markdownlint --config .markdownlint.json "**/*.md"`

**Environment Usage**:

- **VSCode**: Extension: `davidanson.vscode-markdownlint`
- **Make**: `markdownlint --config .markdownlint.json "**/*.md"`
- **Pre-commit**: `markdownlint --config .markdownlint.json`
- **GitHub Actions**: `markdownlint --config .markdownlint.json "**/*.md"`

**Notes**: All environments use the same configuration file.

#### Prettier for Markdown (3.3.3)

**Purpose**: Markdown formatting

**Configuration File**: `.prettierrc`

```json
{
  "overrides": [
    {
      "files": ["*.md"],
      "options": {
        "parser": "markdown",
        "tabWidth": 2,
        "printWidth": 80,
        "proseWrap": "preserve"
      }
    }
  ]
}
```

**Standard Command**: `prettier --check "**/*.md"`

**Environment Usage**:

- **VSCode**: Extension: `esbenp.prettier-vscode`
- **Make**: `prettier --check "**/*.md"`
- **Pre-commit**: `prettier` (files: \.(md|json|ya?ml)$)
- **GitHub Actions**: Via `make lint-markdown`

**Notes**: Used for formatting, markdownlint handles linting.

### YAML/JSON/TOML Validation

#### check-yaml (v6.0.0)

**Purpose**: YAML syntax validation

**Standard Command**: `check-yaml --unsafe`

**Environment Usage**:

- **VSCode**: Extension: `redhat.vscode-yaml`
- **Make**: `yamllint .yamllint **/*.yaml **/*.yml` (if yamllint installed)
- **Pre-commit**: `check-yaml --unsafe`
- **GitHub Actions**: `check-yaml --unsafe`

**Notes**: Pre-commit hook uses `--unsafe` flag for custom tags.

#### check-json (v6.0.0)

**Purpose**: JSON syntax validation

**Standard Command**: `check-json`

**Environment Usage**:

- **VSCode**: Built-in JSON validation
- **Make**: `python -m json.tool < file.json` (basic validation)
- **Pre-commit**: `check-json`
- **GitHub Actions**: `check-json`

#### check-toml (v6.0.0)

**Purpose**: TOML syntax validation

**Standard Command**: `check-toml`

**Environment Usage**:

- **VSCode**: Built-in TOML support
- **Make**: `python -c "import tomli; tomli.loads(open('file.toml').read())"` (basic validation)
- **Pre-commit**: `check-toml`
- **GitHub Actions**: `check-toml`

#### Prettier for YAML/JSON (3.3.3)

**Purpose**: YAML/JSON formatting

**Configuration File**: `.prettierrc`

**Standard Command**: `prettier --check "**/*.{yaml,yml,json}"`

**Environment Usage**:

- **VSCode**: Extension: `esbenp.prettier-vscode`
- **Make**: `prettier --check "**/*.{yaml,yml,json}"`
- **Pre-commit**: `prettier` (files: \.(md|json|ya?ml)$)
- **GitHub Actions**: Via `make lint-yaml` and `make lint-json`

### Terraform Linting

#### terraform fmt (1.13.5)

**Purpose**: Terraform code formatting

**Standard Command**: `terraform fmt -check -recursive`

**Environment Usage**:

- **VSCode**: Extension: `hashicorp.terraform`
- **Make**: `terraform fmt -check -recursive` (via `make lint-terraform-fmt`)
- **Pre-commit**: `terraform fmt -check -recursive`
- **GitHub Actions**: `terraform fmt -check -recursive` (in terraform job)

**Notes**: All environments use the same command.

#### terraform validate (1.13.5)

**Purpose**: Terraform configuration validation

**Standard Command**: `terraform validate`

**Environment Usage**:

- **VSCode**: Extension: `hashicorp.terraform`
- **Make**: `terraform validate` (via `make tf-validate`)
- **Pre-commit**: `terraform validate` (basic validation only)
- **GitHub Actions**: `terraform validate` (in terraform job)

**Notes**: Full validation requires backend initialization (done in CI).

## Environment-Specific Configuration

### VSCode

**Extensions Required**:

- `ms-python.python` - Python language support
- `ms-python.black-formatter` - Black formatter
- `ms-python.flake8` - Flake8 linter
- `dbaeumer.vscode-eslint` - ESLint
- `esbenp.prettier-vscode` - Prettier
- `stylelint.vscode-stylelint` - Stylelint
- `davidanson.vscode-markdownlint` - Markdownlint
- `redhat.vscode-yaml` - YAML support
- `hashicorp.terraform` - Terraform support

**Settings**: See `.vscode/settings.json` for detailed configuration.

### Make

**Targets**:

- `make lint` - Run all linters (Python, MyPy, HTML, CSS, JS)
- `make lint-python` - Python linting only (ruff check, black check)
- `make lint-mypy` - Python type checking only
- `make lint-html` - HTML linting only
- `make lint-css` - CSS linting only
- `make lint-js` - JavaScript linting only
- `make lint-markdown` - Markdown linting
- `make lint-yaml` - YAML validation
- `make lint-json` - JSON validation
- `make lint-toml` - TOML validation
- `make lint-terraform-fmt` - Terraform formatting check
- `make format` - Format all code
- `make format-python` - Format Python code
- `make security-check` - Run security checks (includes Bandit)

### Pre-commit

**Hooks**: See `.pre-commit-config.yaml` for complete hook configuration.

**Key Hooks**:

- File validation (YAML, JSON, TOML, XML)
- Python formatting (Black, ruff check --fix for imports/unused code)
- Python linting (Ruff, MyPy, Bandit)
- JavaScript linting (ESLint via npm)
- HTML linting (Prettier via npm)
- CSS linting (Stylelint via npm)
- Markdown linting (markdownlint, Prettier)
- Terraform formatting (terraform fmt)

### GitHub Actions

**Workflows**: See `.github/workflows/ci.yml` for CI configuration.

**Linting Steps**:

1. Python linting (via `make lint-python`)
2. Python type checking (via `make lint-mypy`)
3. HTML linting (via `make lint-html`)
4. CSS linting (via `make lint-css`)
5. JavaScript linting (via `make lint-js`)
6. Markdown linting (via `make lint-markdown`)
7. YAML/JSON/TOML validation (via `make lint-yaml`, `make lint-json`, `make lint-toml`)
8. Terraform formatting (via `make lint-terraform-fmt`)

## Validation

### Sync Validation Script

Run `make validate-linting-sync` or `scripts/validate-linting-sync.sh` to verify:

- Tool versions match across environments
- Configuration files exist
- Command arguments are consistent
- All discrepancies are reported

### Manual Verification

1. **VSCode**: Install recommended extensions, verify linting works
2. **Make**: Run `make lint` and verify all tools execute
3. **Pre-commit**: Run `pre-commit run --all-files` and verify all hooks pass
4. **GitHub Actions**: Check CI workflow runs successfully

## Troubleshooting

### Common Issues

1. **VSCode extensions not working**: Ensure extensions are installed and enabled
2. **Pre-commit hooks failing**: Run `pre-commit install` to install hooks
3. **Make targets failing**: Ensure virtual environment is activated and dependencies installed
4. **Version mismatches**: Run `make validate-linting-sync` to identify discrepancies

### Getting Help

- Check this documentation first
- Run validation script to identify issues
- Review configuration files for each tool
- Check environment-specific setup in CONTRIBUTING.md

## Maintenance

### Updating Tool Versions

1. Update version in source file (requirements-dev.txt, package.json, .pre-commit-config.yaml)
2. Update this documentation
3. Run validation script to verify consistency
4. Test in all environments

### Adding New Tools

1. Add to appropriate configuration file
2. Add to all four environments
3. Update this documentation
4. Add to validation script
5. Test in all environments

## References

- [Black Documentation](https://black.readthedocs.io/)
- [Flake8 Documentation](https://flake8.pycqa.org/)
- [ESLint Documentation](https://eslint.org/)
- [Prettier Documentation](https://prettier.io/)
- [Stylelint Documentation](https://stylelint.io/)
- [markdownlint Documentation](https://github.com/DavidAnson/markdownlint)
- [Terraform Documentation](https://www.terraform.io/docs)
- [pre-commit Documentation](https://pre-commit.com/)
