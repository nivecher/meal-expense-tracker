#!/bin/bash
# Validate GitHub Actions workflow syntax without requiring act
# This checks YAML syntax and basic workflow structure

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

WORKFLOW_FILE="${1:-.github/workflows/deploy.yml}"

echo -e "${GREEN}🔍 Validating workflow syntax: ${WORKFLOW_FILE}${NC}"
echo ""

# Check if file exists
if [ ! -f "${WORKFLOW_FILE}" ]; then
    echo -e "${RED}❌ Workflow file not found: ${WORKFLOW_FILE}${NC}"
    exit 1
fi

# Check if Python is available (for yamllint or basic validation)
if command -v python3 &> /dev/null; then
    echo -e "${GREEN}✓ Python3 found${NC}"

    # Basic YAML syntax check using Python
    echo "Checking YAML syntax..."
    if python3 -c "import yaml; yaml.safe_load(open('${WORKFLOW_FILE}'))" 2>/dev/null; then
        echo -e "${GREEN}✓ YAML syntax is valid${NC}"
    else
        echo -e "${RED}❌ YAML syntax error${NC}"
        python3 -c "import yaml; yaml.safe_load(open('${WORKFLOW_FILE}'))" 2>&1 || true
        exit 1
    fi
else
    echo -e "${YELLOW}⚠️  Python3 not found, skipping YAML validation${NC}"
fi

# Check for common workflow issues
echo ""
echo "Checking for common issues..."

# Check if workflow has required fields
if grep -q "^name:" "${WORKFLOW_FILE}"; then
    echo -e "${GREEN}✓ Workflow has a name${NC}"
else
    echo -e "${YELLOW}⚠️  Workflow missing 'name' field${NC}"
fi

if grep -q "^on:" "${WORKFLOW_FILE}"; then
    echo -e "${GREEN}✓ Workflow has triggers defined${NC}"
else
    echo -e "${RED}❌ Workflow missing 'on:' triggers${NC}"
    exit 1
fi

if grep -q "^jobs:" "${WORKFLOW_FILE}"; then
    echo -e "${GREEN}✓ Workflow has jobs defined${NC}"
else
    echo -e "${RED}❌ Workflow missing 'jobs:' section${NC}"
    exit 1
fi

# Check for act-specific compatibility
echo ""
echo "Checking act compatibility..."

# Check for workflow_run trigger (act has limited support)
if grep -q "workflow_run:" "${WORKFLOW_FILE}"; then
    echo -e "${YELLOW}⚠️  workflow_run trigger - act has limited support, use workflow_dispatch for testing${NC}"
fi

# Check for workflow_dispatch (good for act)
if grep -q "workflow_dispatch:" "${WORKFLOW_FILE}"; then
    echo -e "${GREEN}✓ workflow_dispatch trigger found (good for act testing)${NC}"
fi

# Check for Docker usage
if grep -q "docker" "${WORKFLOW_FILE}"; then
    echo -e "${GREEN}✓ Docker usage detected (act supports this)${NC}"
fi

# Check for AWS actions (won't work in act)
if grep -q "aws-actions" "${WORKFLOW_FILE}"; then
    echo -e "${YELLOW}⚠️  AWS actions detected - these won't work in act without mocking${NC}"
fi

echo ""
echo -e "${GREEN}✅ Basic validation complete${NC}"
echo ""
echo "To test with act, run:"
echo "  ./scripts/test-deploy-workflow.sh dev --list"
