# Cursor Hooks

This directory contains hooks and scripts for post-generation tasks in Cursor IDE.

## Markdown Linting Hook

After generating markdown files in Cursor, you can automatically fix linting issues using the provided scripts.

### Quick Start

After generating a markdown file in Cursor, run:

```bash
# Fix specific file(s)
./scripts/fix-markdown-linting.sh path/to/file.md

# Fix all markdown files
./scripts/fix-markdown-linting.sh
```

### What It Does

1. **Runs markdownlint with --fix**: Automatically fixes markdown linting issues according to `.markdownlint.json` configuration
2. **Formats with Prettier**: Applies consistent formatting according to `.prettierrc` configuration

### Integration Options

#### Option 1: Manual Execution (Recommended)

After generating markdown files in Cursor, manually run the script:

```bash
./scripts/fix-markdown-linting.sh
```

#### Option 2: Add to Cursor Rules

Add this to your `.cursor/rules/` directory to remind the AI to run the script:

```markdown
# Markdown Generation Rule

After generating any markdown file, always run:
```bash
./scripts/fix-markdown-linting.sh <generated-file.md>
```

This ensures all markdown files follow project linting standards.
```

#### Option 3: Git Pre-commit Hook

The project already has pre-commit hooks configured (see `.pre-commit-config.yaml`), which will automatically lint markdown files on commit. However, you can also add a manual fix step:

```bash
# Add to your git workflow
git add *.md
./scripts/fix-markdown-linting.sh
git add -u  # Stage fixes
git commit
```

#### Option 4: VS Code Task

Create `.vscode/tasks.json`:

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

Then run the task with `Ctrl+Shift+P` → "Tasks: Run Task" → "Fix Markdown Linting"

### Verification

To verify that all issues are fixed, set the `VERIFY` environment variable:

```bash
VERIFY=true ./scripts/fix-markdown-linting.sh
```

### Requirements

- **markdownlint-cli**: `npm install -g markdownlint-cli@0.38.0`
- **prettier**: Available via npm (will use npx if not globally installed)

The scripts will attempt to install markdownlint-cli automatically if it's not found.

### Configuration Files

- `.markdownlint.json` - Markdown linting rules
- `.prettierrc` - Prettier formatting rules (includes markdown-specific settings)

### Troubleshooting

**Script fails with "command not found"**:
- Ensure Node.js and npm are installed
- Install markdownlint-cli: `npm install -g markdownlint-cli@0.38.0`

**Prettier not found**:
- The script will automatically use `npx prettier` if prettier is not globally installed
- Ensure npm is available

**Permission denied**:
- Make scripts executable: `chmod +x scripts/fix-markdown-linting.sh`
