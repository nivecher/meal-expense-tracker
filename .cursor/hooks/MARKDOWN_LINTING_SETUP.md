# Markdown Linting Hook Setup

## Overview

This setup provides automatic markdown linting fixes after generating markdown files in Cursor IDE. The system includes:

1. **Shell script** (`scripts/fix-markdown-linting.sh`) - Script for fixing markdown issues
2. **Cursor rule** (`.cursor/rules/markdown-generation.mdc`) - Instructs AI to run the script automatically
3. **Post-generation hook** (`.cursor/hooks/post-generate-markdown.sh`) - Convenience wrapper

## Quick Start

### After Generating a Markdown File

Simply run:

```bash
./scripts/fix-markdown-linting.sh <your-file.md>
```

Or fix all markdown files:

```bash
./scripts/fix-markdown-linting.sh
```

### What Gets Fixed

The script automatically:

- ✅ Fix markdownlint issues (according to `.markdownlint.json`)
- ✅ Format with Prettier (according to `.prettierrc`)
- ✅ Ensure consistent line lengths, spacing, and formatting

## Files Created

### Scripts

- `scripts/fix-markdown-linting.sh` - Bash script for fixing markdown linting issues

### Cursor Integration

- `.cursor/rules/markdown-generation.mdc` - Rule that instructs AI to run the script
- `.cursor/hooks/post-generate-markdown.sh` - Convenience wrapper hook
- `.cursor/hooks/README.md` - Detailed documentation

## How It Works

1. **Markdownlint** (`--fix` flag) automatically fixes:

   - Heading styles
   - List formatting
   - Line length issues
   - Spacing problems
   - And more (see `.markdownlint.json`)

2. **Prettier** formats:
   - Line wrapping (80 chars for prose)
   - Indentation (2 spaces)
   - Consistent formatting

## Integration with Cursor AI

The `.cursor/rules/markdown-generation.mdc` rule ensures that when you ask Cursor to generate markdown files, it will automatically run the fix script afterward.

Example:

```
User: "Create a README.md file for the new feature"
Cursor: [Generates README.md]
Cursor: [Automatically runs] ./scripts/fix-markdown-linting.sh README.md
```

## Manual Usage

### Fix Specific Files

```bash
./scripts/fix-markdown-linting.sh docs/NEW_FEATURE.md README.md
```

### Fix All Markdown Files

```bash
./scripts/fix-markdown-linting.sh
```

### Verify Fixes

```bash
VERIFY=true ./scripts/fix-markdown-linting.sh
```

## Requirements

- **Node.js** and **npm** (for markdownlint and prettier)
- **markdownlint-cli**: Will be auto-installed if missing
- **prettier**: Available via npm (uses npx if not globally installed)

## Configuration

The scripts use existing project configuration:

- `.markdownlint.json` - Markdown linting rules
- `.prettierrc` - Formatting rules (includes markdown-specific settings)

## Troubleshooting

### "command not found" errors

```bash
# Install markdownlint-cli
npm install -g markdownlint-cli@0.38.0

# Verify Node.js/npm
node --version
npm --version
```

### Permission denied

```bash
chmod +x scripts/fix-markdown-linting.sh
```

### Script doesn't find files

- Ensure you're in the repository root
- Check that files exist and have `.md` extension
- Verify files aren't in excluded directories (node_modules, venv, etc.)

## Integration Options

### Option 1: Manual (Current)

Run the script manually after generating markdown files.

### Option 2: Cursor Rule (Recommended)

The `.cursor/rules/markdown-generation.mdc` rule instructs Cursor AI to automatically run the script.

### Option 3: Pre-commit Hook

Already configured in `.pre-commit-config.yaml` - will lint on commit.

### Option 4: VS Code Task

Add to `.vscode/tasks.json`:

```json
{
  "version": "2.0.0",
  "tasks": [
    {
      "label": "Fix Markdown Linting",
      "type": "shell",
      "command": "${workspaceFolder}/scripts/fix-markdown-linting.sh",
      "problemMatcher": []
    }
  ]
}
```

## Benefits

✅ **Automatic**: No manual linting fixes needed  
✅ **Consistent**: All markdown files follow the same standards  
✅ **CI/CD Ready**: Files pass pre-commit hooks  
✅ **Fast**: Fixes applied in seconds  
✅ **Safe**: Non-destructive fixes only

## Related Documentation

- `.cursor/hooks/README.md` - Detailed hook documentation
- `.cursor/rules/markdown-generation.mdc` - Cursor rule definition
- `docs/LINTING_STANDARDS.md` - Project linting standards
- `.markdownlint.json` - Markdown linting configuration
- `.prettierrc` - Prettier configuration
