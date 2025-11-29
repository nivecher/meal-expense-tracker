#!/bin/bash
# validate-linting-sync.sh
# Validates that linting tool versions and configurations are consistent across all environments

set -eu pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Track discrepancies
DISCREPANCIES=0
WARNINGS=0

echo "🔍 Validating linting tool synchronization across environments..."
echo ""

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to get Python package version
get_python_version() {
    local package=$1
    if command_exists python3 && python3 -m pip show "$package" >/dev/null 2>&1; then
        python3 -m pip show "$package" 2>/dev/null | grep "^Version:" | awk '{print $2}' || echo "not-installed"
    else
        echo "not-installed"
    fi
}

# Function to get npm package version
get_npm_version() {
    local package=$1
    if command_exists npm && [ -f package.json ]; then
        npm list "$package" 2>/dev/null | grep "$package@" | sed "s/.*$package@\([0-9.]*\).*/\1/" | head -1 || echo "not-installed"
    else
        echo "not-installed"
    fi
}

# Function to check version in requirements file
get_requirements_version() {
    local package=$1
    local file=$2
    if [ -f "$file" ]; then
        grep -i "^$package==" "$file" 2>/dev/null | sed "s/.*==\([0-9.]*\).*/\1/" | head -1 || echo "not-found"
    else
        echo "file-not-found"
    fi
}

# Function to check version in package.json
get_package_json_version() {
    local package=$1
    if [ -f package.json ]; then
        grep -A 5 "\"$package\"" package.json 2>/dev/null | grep "version" | sed 's/.*"version": *"\([^"]*\)".*/\1/' | head -1 || \
        grep "\"$package\"" package.json 2>/dev/null | sed 's/.*"'"$package"'": *"\([^"]*\)".*/\1/' | head -1 || echo "not-found"
    else
        echo "file-not-found"
    fi
}

# Function to check version in pre-commit config
get_precommit_version() {
    local repo_url=$1
    if [ -f .pre-commit-config.yaml ]; then
        grep -A 2 "$repo_url" .pre-commit-config.yaml 2>/dev/null | grep "rev:" | sed 's/.*rev: *\([^ ]*\).*/\1/' | head -1 || echo "not-found"
    else
        echo "file-not-found"
    fi
}

# Function to report discrepancy
report_discrepancy() {
    local tool=$1
    local env=$2
    local expected=$3
    local actual=$4
    echo -e "${RED}❌ DISCREPANCY:${NC} $tool in $env"
    echo "   Expected: $expected"
    echo "   Actual: $actual"
    ((DISCREPANCIES++))
}

# Function to report warning
report_warning() {
    local message=$1
    echo -e "${YELLOW}⚠️  WARNING:${NC} $message"
    ((WARNINGS++))
}

# Function to report success
report_success() {
    local tool=$1
    local version=$2
    echo -e "${GREEN}✅${NC} $tool: $version"
}

echo "=== Python Tools ==="

# Black
BLACK_REQ=$(get_requirements_version "black" "requirements-dev.txt")
BLACK_PRECOMMIT=$(get_precommit_version "github.com/psf/black")
if [ "$BLACK_REQ" != "$BLACK_PRECOMMIT" ] && [ "$BLACK_REQ" != "not-found" ] && [ "$BLACK_PRECOMMIT" != "not-found" ]; then
    report_discrepancy "Black" "requirements vs pre-commit" "$BLACK_REQ" "$BLACK_PRECOMMIT"
else
    report_success "Black" "${BLACK_REQ:-${BLACK_PRECOMMIT:-unknown}}"
fi

# Flake8
FLAKE8_REQ=$(get_requirements_version "flake8" "requirements-dev.txt")
FLAKE8_PRECOMMIT=$(get_precommit_version "github.com/pycqa/flake8")
if [ "$FLAKE8_REQ" != "$FLAKE8_PRECOMMIT" ] && [ "$FLAKE8_REQ" != "not-found" ] && [ "$FLAKE8_PRECOMMIT" != "not-found" ]; then
    report_discrepancy "Flake8" "requirements vs pre-commit" "$FLAKE8_REQ" "$FLAKE8_PRECOMMIT"
else
    report_success "Flake8" "${FLAKE8_REQ:-${FLAKE8_PRECOMMIT:-unknown}}"
fi

# isort
ISORT_REQ=$(get_requirements_version "isort" "requirements-dev.txt")
ISORT_PRECOMMIT=$(get_precommit_version "github.com/pycqa/isort")
if [ "$ISORT_REQ" != "$ISORT_PRECOMMIT" ] && [ "$ISORT_REQ" != "not-found" ] && [ "$ISORT_PRECOMMIT" != "not-found" ]; then
    report_discrepancy "isort" "requirements vs pre-commit" "$ISORT_REQ" "$ISORT_PRECOMMIT"
else
    report_success "isort" "${ISORT_REQ:-${ISORT_PRECOMMIT:-unknown}}"
fi

# autoflake
AUTOFLAKE_REQ=$(get_requirements_version "autoflake" "requirements-dev.txt")
AUTOFLAKE_PRECOMMIT=$(get_precommit_version "github.com/PyCQA/autoflake")
# Remove 'v' prefix from pre-commit version for comparison
AUTOFLAKE_PRECOMMIT_CLEAN=$(echo "$AUTOFLAKE_PRECOMMIT" | sed 's/^v//')
if [ "$AUTOFLAKE_REQ" != "$AUTOFLAKE_PRECOMMIT_CLEAN" ] && [ "$AUTOFLAKE_REQ" != "not-found" ] && [ "$AUTOFLAKE_PRECOMMIT_CLEAN" != "" ] && [ "$AUTOFLAKE_PRECOMMIT_CLEAN" != "not-found" ]; then
    report_discrepancy "autoflake" "requirements vs pre-commit" "$AUTOFLAKE_REQ" "$AUTOFLAKE_PRECOMMIT"
else
    report_success "autoflake" "${AUTOFLAKE_REQ:-${AUTOFLAKE_PRECOMMIT_CLEAN:-unknown}}"
fi

# Bandit
BANDIT_REQ=$(get_requirements_version "bandit" "requirements-dev.txt")
BANDIT_PRECOMMIT=$(get_precommit_version "github.com/PyCQA/bandit")
if [ "$BANDIT_REQ" != "$BANDIT_PRECOMMIT" ] && [ "$BANDIT_REQ" != "not-found" ] && [ "$BANDIT_PRECOMMIT" != "not-found" ]; then
    report_discrepancy "Bandit" "requirements vs pre-commit" "$BANDIT_REQ" "$BANDIT_PRECOMMIT"
else
    report_success "Bandit" "${BANDIT_REQ:-${BANDIT_PRECOMMIT:-unknown}}"
fi

echo ""
echo "=== JavaScript/Web Tools ==="

# ESLint
ESLINT_PKG=$(get_package_json_version "eslint")
if [ "$ESLINT_PKG" = "not-found" ]; then
    report_warning "ESLint version not found in package.json"
else
    report_success "ESLint" "$ESLINT_PKG"
fi

# Prettier
PRETTIER_PKG=$(get_package_json_version "prettier")
PRETTIER_PRECOMMIT=$(get_precommit_version "github.com/pre-commit/mirrors-prettier")
# Extract version from additional_dependencies
PRETTIER_PRECOMMIT_DEPS=$(grep -A 2 "pre-commit/mirrors-prettier" .pre-commit-config.yaml 2>/dev/null | grep "prettier@" | sed 's/.*prettier@\([0-9.]*\).*/\1/' | head -1 || echo "not-found")
if [ "$PRETTIER_PKG" != "$PRETTIER_PRECOMMIT_DEPS" ] && [ "$PRETTIER_PKG" != "not-found" ] && [ "$PRETTIER_PRECOMMIT_DEPS" != "not-found" ]; then
    report_discrepancy "Prettier" "package.json vs pre-commit" "$PRETTIER_PKG" "$PRETTIER_PRECOMMIT_DEPS"
else
    report_success "Prettier" "${PRETTIER_PKG:-${PRETTIER_PRECOMMIT_DEPS:-unknown}}"
fi

# Stylelint
STYLELINT_PKG=$(get_package_json_version "stylelint")
if [ "$STYLELINT_PKG" = "not-found" ]; then
    report_warning "Stylelint version not found in package.json"
else
    report_success "Stylelint" "$STYLELINT_PKG"
fi

echo ""
echo "=== Configuration Files ==="

# Check for required config files
CONFIG_FILES=(
    ".flake8:Flake8"
    ".bandit:Bandit"
    "pyproject.toml:Black/isort"
    "eslint.config.js:ESLint"
    ".stylelintrc.json:Stylelint"
    ".markdownlint.json:Markdownlint"
    ".prettierrc:Prettier"
    ".yamllint:YAML"
)

for config in "${CONFIG_FILES[@]}"; do
    IFS=':' read -r file tool <<< "$config"
    if [ -f "$file" ]; then
        report_success "$tool config" "exists"
    else
        report_warning "${tool} config file '${file}' not found"
    fi
done

echo ""
echo "=== Makefile Targets ==="

# Check if Makefile has required targets
MAKEFILE_TARGETS=(
    "lint-python"
    "lint-html"
    "lint-css"
    "lint-js"
    "lint-markdown"
    "lint-yaml"
    "lint-json"
    "lint-toml"
    "lint-terraform-fmt"
)

for target in "${MAKEFILE_TARGETS[@]}"; do
    if grep -q "^\.PHONY: $target" Makefile 2>/dev/null || grep -q "^##.*$target" Makefile 2>/dev/null; then
        report_success "Makefile target" "$target"
    else
        report_warning "Makefile target '$target' not found"
    fi
done

echo ""
echo "=== Pre-commit Hooks ==="

# Check if pre-commit config has required hooks
PRECOMMIT_HOOKS=(
    "black:Python formatting"
    "flake8:Python linting"
    "isort:Import sorting"
    "autoflake:Remove unused imports"
    "bandit:Security scanning"
    "markdownlint:Markdown linting"
    "prettier:Code formatting"
    "terraform_fmt:Terraform formatting"
)

for hook_info in "${PRECOMMIT_HOOKS[@]}"; do
    IFS=':' read -r hook_id hook_name <<< "$hook_info"
    if grep -q "id: $hook_id" .pre-commit-config.yaml 2>/dev/null; then
        report_success "Pre-commit hook" "$hook_name"
    else
        report_warning "Pre-commit hook '$hook_name' with id '$hook_id' not found"
    fi
done

echo ""
echo "=== Summary ==="



if [ $DISCREPANCIES -eq 0 ] && [ $WARNINGS -eq 0 ]; then
    echo -e "${GREEN}All linting tools are synchronized!${NC}"
    exit 0
elif [ $DISCREPANCIES -eq 0 ]; then
    if [ $WARNINGS -eq 1 ]; then
        echo -e "${YELLOW}Validation completed with ${WARNINGS} warning${NC}"
    else
        echo -e "${YELLOW}Validation completed with ${WARNINGS} warnings${NC}"
    fi
    exit 0
else
    disc_text="discrepancy"
    warn_text="warning"
    [ $DISCREPANCIES -ne 1 ] && disc_text="discrepancies"
    [ $WARNINGS -ne 1 ] && warn_text="warnings"
    echo -e "${RED}Validation failed: ${DISCREPANCIES} ${disc_text} and ${WARNINGS} ${warn_text}${NC}"
    exit 1
fi
