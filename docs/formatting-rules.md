# Formatting Rules

This document explains the formatting configuration for the Meal Expense Tracker project.

## HTML Template Formatting (djlint)

We use `djlint` to format HTML templates with Jinja2 syntax. The configuration prevents common issues with quote changes in template expressions.

### Key Configuration

- **Profile**: `jinja` (not django) to properly handle Jinja2 syntax
- **Ignored Rule H031**: Prevents changing single quotes to double quotes in expressions like `{{ url_for('main.about') }}`

### Why This Matters

The Flask `url_for` function expects single quotes inside Jinja2 expressions:

```html
<!-- CORRECT -->
<a href="{{ url_for('main.about') }}">About</a>

<!-- INCORRECT (breaks functionality) -->
<a href="{{ url_for("main.about") }}">About</a>
```

### Running Formatters

```bash
# Format HTML templates (safe for Jinja2)
make format-html

# Lint HTML templates
make lint-html

# Format all code
make format
```

### Configuration Files

- `.djlintrc` - djlint-specific configuration
- `pyproject.toml` - Python project configuration including djlint settings
- `Makefile` - Build targets with correct djlint arguments

## Quote Style Standards

**Python Code (Black formatter):**

- **Double quotes** for all Python strings: `"hello world"`
- Black enforces this automatically and cannot be configured otherwise
- This follows PEP 8 and Python community standards

**JavaScript Code (ESLint):**

- **Single quotes** for JS strings: `'hello world'`
- Avoids escaping in HTML context: `element.innerHTML = '<div class="content">Hello</div>'`

**Jinja2 Templates:**

- **Single quotes** inside expressions: `{{ url_for('main.about') }}`
- **Double quotes** for HTML attributes: `<div class="container">`

**YAML/Config Files:**

- **Single quotes** when quotes are needed: `quote-type: 'single'`

## Other Formatters

- **Python**: Black with 120 character line length (double quotes enforced)
- **JavaScript**: ESLint with single quotes preference
- **CSS**: Stylelint (if configured)

## Pre-commit Hooks

The project uses pre-commit hooks to automatically format code before commits. See `.pre-commit-config.yaml` for details.
