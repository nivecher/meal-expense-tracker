# Development Tools Setup

This document describes the controlled development tools setup for the Meal Expense Tracker project, ensuring reproducible builds and consistent development environments.

## Overview

All development tools are pinned to specific versions through a controlled requirements system to ensure:

- **Reproducible builds** across different environments
- **Consistent code quality** standards
- **Predictable CI/CD** behavior
- **Security** through known, tested versions

## Requirements System Architecture

### Core Files

```
requirements/
├── base.in          # Production dependencies (input)
├── dev.in           # Development dependencies (input)
├── base.txt         # Generated production requirements
└── dev.txt          # Generated development requirements

requirements-dev.txt  # Symlink to requirements/dev.txt
requirements.txt      # Symlink to requirements/base.txt
constraints.txt       # Version constraints for reproducible builds
```

### Generation Process

```bash
# Generate all requirements
make requirements

# Generate production only
make requirements-prod

# Generate development only
make requirements-dev
```

## Python Development Tools

### Core Tools (Pinned Versions)

| Tool       | Version | Purpose             | Configuration    |
| ---------- | ------- | ------------------- | ---------------- |
| **black**  | 24.10.0 | Code formatting     | `pyproject.toml` |
| **flake8** | 7.3.0   | Linting             | `.flake8`        |
| **isort**  | 5.13.2  | Import sorting      | `pyproject.toml` |
| **mypy**   | 1.13.0  | Type checking       | `pyproject.toml` |
| **pylint** | 3.3.1   | Static analysis     | Built-in config  |
| **bandit** | 1.8.6   | Security linting    | `.bandit`        |
| **safety** | 3.7.0   | Dependency security | Auto-updated     |

### Testing Tools (Pinned Versions)

| Tool             | Version | Purpose              | Configuration    |
| ---------------- | ------- | -------------------- | ---------------- |
| **pytest**       | 8.4.2   | Test framework       | `pyproject.toml` |
| **pytest-cov**   | 4.0.0   | Coverage reporting   | `pyproject.toml` |
| **pytest-xdist** | 3.8.0   | Parallel testing     | CLI flags        |
| **coverage**     | 7.6.9   | Coverage measurement | `pyproject.toml` |
| **factory-boy**  | 3.3.3   | Test fixtures        | N/A              |
| **Faker**        | 25.9.2  | Test data generation | N/A              |

### Documentation Tools (Pinned Versions)

| Tool                 | Version | Purpose                  | Configuration  |
| -------------------- | ------- | ------------------------ | -------------- |
| **sphinx**           | 7.4.7   | Documentation generation | `docs/conf.py` |
| **sphinx-rtd-theme** | 2.0.0   | Documentation theme      | `docs/conf.py` |

## Node.js Development Tools

### Package Management

Most Node.js dependencies are pinned in `package.json` without version ranges, with security exceptions:

```json
{
  "devDependencies": {
    "eslint-formatter-compact": "8.40.0",
    "prettier": "3.3.3",
    "stylelint": "16.24.0",
    "stylelint-config-standard": "39.0.0"
  },
  "dependencies": {
    "@playwright/test": "^1.56.1",
    "eslint": "9.34.0"
  }
}
```

**Security Exception**: Playwright uses a caret range (`^1.56.1`) to allow automatic security updates while maintaining compatibility within the same major version.

### Tool Purposes

| Tool           | Purpose            | Configuration          |
| -------------- | ------------------ | ---------------------- |
| **ESLint**     | JavaScript linting | `eslint.config.js`     |
| **Prettier**   | Code formatting    | `.prettierrc`          |
| **Stylelint**  | CSS linting        | `.stylelintrc.json`    |
| **Playwright** | End-to-end testing | `playwright.config.js` |

## Pre-commit Hooks

Pre-commit hooks use pinned versions that match our requirements:

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/psf/black
    rev: 24.10.0 # Matches requirements/dev.in

  - repo: https://github.com/pycqa/flake8
    rev: 7.3.0 # Matches requirements/dev.in

  - repo: https://github.com/pycqa/isort
    rev: 5.13.2 # Matches requirements/dev.in


  # Prettier disabled - mirrors-prettier repo has version sync issues
  # Use npm scripts instead: npm run format-html
  # - repo: https://github.com/pre-commit/mirrors-prettier
  #   rev: 3.3.3
  #   hooks:
  #     - id: prettier
```

## GitHub Actions

GitHub Actions use pinned versions for all actions:

```yaml
# .github/workflows/ci.yml
steps:
  - uses: actions/checkout@v4.2.2
  - uses: actions/setup-python@v5.3.0
  - uses: actions/setup-node@v4.1.0
```

## Version Constraints

The `constraints.txt` file pins critical packages to ensure reproducible builds:

```txt
# Core Flask ecosystem
click==8.1.7
Flask==3.1.1
Werkzeug==3.1.3

# Development tools
black==24.10.0
flake8==7.3.0
pytest==8.4.2
```

## Development Workflow

### Initial Setup

```bash
# 1. Install Python dependencies
pip install -r requirements-dev.txt

# 2. Install Node.js dependencies
npm install

# 3. Install pre-commit hooks
pre-commit install

# 4. Verify setup
make lint
make test-fast
```

### Adding New Dependencies

#### Python Dependencies

1. Add to appropriate `.in` file:

   ```bash
   # For production
   echo "new-package>=1.0.0,<2.0.0" >> requirements/base.in

   # For development
   echo "new-dev-tool>=1.0.0,<2.0.0" >> requirements/dev.in
   ```

2. Regenerate requirements:

   ```bash
   make requirements
   ```

3. Update constraints if needed:
   ```bash
   echo "new-package==1.2.3" >> constraints.txt
   ```

#### Node.js Dependencies

1. Install with exact version:

   ```bash
   npm install --save-exact new-package@1.2.3
   ```

2. Verify `package.json` has no version ranges (no `^` or `~`)

### Updating Dependencies

#### Python Dependencies

```bash
# Update all dependencies
make requirements-upgrade

# Update specific dependency
pip-compile --upgrade-package package-name requirements/dev.in
```

#### Node.js Dependencies

```bash
# Check for updates
npm outdated

# Update specific package
npm install --save-exact package-name@new-version
```

## Quality Assurance

### Automated Checks

```bash
# Run all quality checks
make lint          # Python linting
make lint-js       # JavaScript linting
make lint-css      # CSS linting
make test-fast     # Fast test suite
make test          # Full test suite
```

### Pre-commit Validation

All commits are automatically validated for:

- Code formatting (Black, Prettier)
- Linting (flake8, ESLint, Stylelint)
- Security (Bandit)
- Import sorting (isort)
- File validation (YAML, JSON, TOML)

### CI/CD Pipeline

The GitHub Actions pipeline validates:

1. **Lint Job**: Fast feedback on code quality
2. **Test Job**: Comprehensive test suite
3. **Security Job**: Dependency vulnerability scanning
4. **Build Job**: Application build verification

## Security Considerations

### Dependency Scanning

- **Safety**: Scans Python dependencies for known vulnerabilities
- **Bandit**: Scans Python code for security issues
- **npm audit**: Scans Node.js dependencies for vulnerabilities
- **Dependabot**: Automated dependency updates (configured in `.github/dependabot.yml`)

### Security Update Policy

#### Python Dependencies

- **Exact versions** for reproducibility
- **Manual updates** for security patches after testing
- **Safety scanning** in CI/CD pipeline

#### Node.js Dependencies

- **Exact versions** for most packages
- **Caret ranges** for security-critical packages (e.g., Playwright: `^1.56.1`)
- **Automatic security updates** within compatible version ranges
- **npm audit** in CI/CD pipeline

### Version Pinning Benefits

1. **Reproducible Builds**: Exact same versions across environments
2. **Security**: Known, tested versions with controlled security updates
3. **Stability**: Prevents breaking changes from automatic updates
4. **Debugging**: Easier to isolate issues to code changes vs dependency changes
5. **Flexibility**: Security exceptions allow critical updates when needed

## Troubleshooting

### Common Issues

#### Dependency Conflicts

```bash
# Clear pip cache
pip cache purge

# Regenerate from scratch
rm requirements-dev.txt requirements.txt
make requirements
```

#### Node.js Issues

```bash
# Clear npm cache
npm cache clean --force

# Remove and reinstall
rm -rf node_modules package-lock.json
npm install
```

#### Pre-commit Issues

```bash
# Update pre-commit
pre-commit autoupdate

# Clear pre-commit cache
pre-commit clean
```

### Version Compatibility

If you encounter version conflicts:

1. Check `constraints.txt` for conflicting pins
2. Update the conflicting package version range in `.in` files
3. Regenerate requirements
4. Test thoroughly before committing

## Best Practices

### DO

✅ **Pin exact versions** in `constraints.txt` for critical packages  
✅ **Use version ranges** in `.in` files for flexibility  
✅ **Test after updates** to ensure compatibility  
✅ **Document breaking changes** in commit messages  
✅ **Update pre-commit hooks** to match requirements

### DON'T

❌ **Don't use version ranges** in `package.json`  
❌ **Don't skip regenerating** requirements after changes  
❌ **Don't commit** generated files without testing  
❌ **Don't mix** development and production dependencies  
❌ **Don't ignore** security warnings from safety/bandit

## Maintenance Schedule

- **Weekly**: Check for security updates with `safety check`
- **Monthly**: Review and update development tool versions
- **Quarterly**: Major dependency updates and compatibility testing
- **As needed**: Critical security patches

## References

- [pip-tools Documentation](https://pip-tools.readthedocs.io/)
- [Pre-commit Documentation](https://pre-commit.com/)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Python Packaging Guide](https://packaging.python.org/)
