#!/usr/bin/env bash
# Post-generation hook for markdown files
# This script is automatically called after markdown files are generated in Cursor
#
# Usage: This can be integrated into Cursor rules or run manually

set -euo pipefail

# Get the repository root
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$REPO_ROOT"

# Get the file(s) that were just generated
# If files are passed as arguments, use those; otherwise, find recently modified .md files
if [ $# -gt 0 ]; then
    FILES=("$@")
else
    # Find markdown files modified in the last 5 minutes
    mapfile -t FILES < <(find . -type f -name "*.md" \
        ! -path "./node_modules/*" \
        ! -path "./venv/*" \
        ! -path "./.venv/*" \
        ! -path "./.git/*" \
        -mmin -5)
fi

if [ ${#FILES[@]} -eq 0 ]; then
    echo "No markdown files to process."
    exit 0
fi

echo "🔧 Fixing markdown linting for ${#FILES[@]} file(s)..."

# Run the main fix script
"$REPO_ROOT/scripts/fix-markdown-linting.sh" "${FILES[@]}"
