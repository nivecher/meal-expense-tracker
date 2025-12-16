#!/usr/bin/env bash
# Fix markdown linting issues after generating markdown files
# This script runs markdownlint with --fix and prettier to format markdown files

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get the repository root directory
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$REPO_ROOT"

# Check if markdownlint is available
if ! command -v markdownlint >/dev/null 2>&1; then
    echo -e "${YELLOW}⚠️  markdownlint-cli not found. Installing...${NC}"
    if command -v npm >/dev/null 2>&1; then
        npm install -g markdownlint-cli@0.38.0
    else
        echo -e "${RED}❌ npm not found. Please install Node.js and npm first.${NC}"
        exit 1
    fi
fi

# Check if prettier is available
if ! command -v prettier >/dev/null 2>&1; then
    echo -e "${YELLOW}⚠️  prettier not found. Checking for npx...${NC}"
    if ! command -v npx >/dev/null 2>&1; then
        echo -e "${RED}❌ npx not found. Please install Node.js and npm first.${NC}"
        exit 1
    fi
    USE_NPX=true
else
    USE_NPX=false
fi

# Get list of markdown files to process
# If files are provided as arguments, use those; otherwise, find all .md files
if [ $# -gt 0 ]; then
    MD_FILES=("$@")
else
    echo -e "${GREEN}📝 Finding all markdown files...${NC}"
    # Find all .md files excluding node_modules, venv, .git, etc.
    mapfile -t MD_FILES < <(find . -type f -name "*.md" \
        ! -path "./node_modules/*" \
        ! -path "./venv/*" \
        ! -path "./.venv/*" \
        ! -path "./.git/*" \
        ! -path "./dist/*" \
        ! -path "./build/*" \
        ! -path "./.pytest_cache/*" \
        ! -path "./.mypy_cache/*")
fi

if [ ${#MD_FILES[@]} -eq 0 ]; then
    echo -e "${YELLOW}⚠️  No markdown files found to process.${NC}"
    exit 0
fi

echo -e "${GREEN}🔧 Fixing markdown linting issues for ${#MD_FILES[@]} file(s)...${NC}"

# Step 1: Run markdownlint with --fix
echo -e "\n${GREEN}Step 1: Running markdownlint --fix...${NC}"
if [ $# -gt 0 ]; then
    # Process specific files
    markdownlint --config .markdownlint.json --fix "${MD_FILES[@]}" || true
else
    # Process all files
    markdownlint --config .markdownlint.json --fix "**/*.md" || true
fi

# Step 2: Format with prettier
echo -e "\n${GREEN}Step 2: Formatting with prettier...${NC}"
if [ "$USE_NPX" = true ]; then
    for file in "${MD_FILES[@]}"; do
        if [ -f "$file" ]; then
            npx --yes prettier@3.3.3 --write "$file" || true
        fi
    done
else
    for file in "${MD_FILES[@]}"; do
        if [ -f "$file" ]; then
            prettier --write "$file" || true
        fi
    done
fi

echo -e "\n${GREEN}✅ Markdown linting fixes complete!${NC}"

# Step 3: Verify (optional)
if [ "${VERIFY:-false}" = "true" ]; then
    echo -e "\n${GREEN}Step 3: Verifying markdown files...${NC}"
    if [ $# -gt 0 ]; then
        markdownlint --config .markdownlint.json "${MD_FILES[@]}" || {
            echo -e "${YELLOW}⚠️  Some issues remain. Please review manually.${NC}"
            exit 1
        }
    else
        markdownlint --config .markdownlint.json "**/*.md" || {
            echo -e "${YELLOW}⚠️  Some issues remain. Please review manually.${NC}"
            exit 1
        }
    fi
    echo -e "${GREEN}✅ All markdown files pass linting!${NC}"
fi
