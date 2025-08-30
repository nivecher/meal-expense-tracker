# Quote Style Guide

This document explains the quote style conventions for different file types in the Meal Expense Tracker project.

## The Problem

Different formatters have different quote preferences, leading to "thrashing" where files get changed back and forth between single and double quotes. This guide establishes clear rules to prevent conflicts.

## Quote Style by File Type

### Python Files (.py)

- **Use double quotes**: `"hello world"`
- **Formatter**: Black (cannot be configured to use single quotes)
- **Rationale**: Black is the official Python formatter and enforces double quotes

```python
# ✅ Correct
message = "Hello world"
error_msg = "User 'admin' not found"

# ❌ Incorrect (Black will change these)
message = 'Hello world'
```

### JavaScript Files (.js)

- **Use single quotes**: `'hello world'`
- **Formatter**: ESLint
- **Rationale**: Avoids escaping when working with HTML

```javascript
// ✅ Correct
const message = 'Hello world';
element.innerHTML = '<div class="content">Data</div>';

// ❌ Incorrect
const message = 'Hello world';
```

### Jinja2 Templates (.html, .jinja, .j2)

- **Single quotes inside Jinja expressions**: `{{ url_for('route') }}`
- **Double quotes for HTML attributes**: `<div class="container">`
- **Formatter**: djlint with H031 rule disabled

```html
<!-- ✅ Correct -->
<a href="{{ url_for('main.about') }}" class="btn btn-primary">About</a>

<!-- ❌ Incorrect (breaks Flask routing) -->
<a href="{{ url_for("main.about") }}" class="btn btn-primary">About</a>
```

### Configuration Files

- **YAML**: Single quotes when needed: `quote-type: 'single'`
- **JSON**: Double quotes (JSON standard): `{"key": "value"}`
- **TOML**: Double quotes: `key = "value"`

## Formatter Configuration

### Black (Python)

```toml
[tool.black]
# No quote configuration - always uses double quotes
line-length = 120
```

### ESLint (JavaScript)

```javascript
'quotes': ['error', 'single', { avoidEscape: true }]
```

### djlint (HTML/Jinja2)

```ini
# .djlintrc
profile=jinja
ignore=H031  # Disable quote enforcement
```

## Pre-commit Hooks

The pre-commit configuration runs formatters in this order:

1. Black (Python) - enforces double quotes
2. ESLint (JavaScript) - enforces single quotes
3. djlint (Templates) - preserves single quotes in Jinja expressions

## Common Conflicts and Solutions

### Python Script Changes Quotes

**Problem**: Running `make format-python` changes single to double quotes
**Solution**: This is correct behavior - use double quotes in Python

### Template Formatter Breaks url_for

**Problem**: djlint changes `url_for('route')` to `url_for("route")`
**Solution**: Use the updated .djlintrc with `ignore=H031`

### JavaScript Linter Complains About Double Quotes

**Problem**: ESLint errors on `"string"` literals
**Solution**: Use single quotes in JavaScript files

## Testing the Configuration

```bash
# Test Python formatting (should use double quotes)
echo 'print("hello")' > test.py && python -m black test.py && cat test.py

# Test JavaScript formatting (should use single quotes)
echo 'const msg = "hello";' > test.js && npx eslint --fix test.js && cat test.js

# Test template formatting (should preserve url_for quotes)
echo '<a href="{{ url_for('\''main.about'\'') }}">About</a>' > test.html && python -m djlint test.html --reformat && cat test.html
```

## Recommended Workflow

1. Write code using the appropriate quote style for each file type
2. Run `make format` to apply all formatters
3. Commit changes - pre-commit hooks will enforce consistency
4. No manual quote changes should be needed
