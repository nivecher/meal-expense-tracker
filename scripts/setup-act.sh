#!/bin/bash
# Setup script for act (GitHub Actions local runner)

set -euo pipefail

echo "🚀 Setting up act for local GitHub Actions execution..."

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Check if act is already installed
if command -v act >/dev/null 2>&1; then
    echo -e "${GREEN}✅ act is already installed${NC}"
    act --version
else
    echo -e "${YELLOW}📦 Installing act...${NC}"

    # Install act
    curl https://raw.githubusercontent.com/nektos/act/master/install.sh | sudo bash

    if command -v act >/dev/null 2>&1; then
        echo -e "${GREEN}✅ act installed successfully${NC}"
        act --version
    else
        echo -e "${RED}❌ Failed to install act${NC}"
        exit 1
    fi
fi

# Create .env.local file if it doesn't exist
if [ ! -f ".env.local" ]; then
    echo -e "${YELLOW}📝 Creating .env.local file...${NC}"
    cp scripts/act-config.env .env.local
    echo -e "${YELLOW}⚠️  Please edit .env.local and add your actual values${NC}"
    echo -e "${YELLOW}   Required: GITHUB_TOKEN, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY${NC}"
else
    echo -e "${GREEN}✅ .env.local already exists${NC}"
fi

# Create .act directory for act configuration
mkdir -p .act

# Test act installation
echo -e "\n${BLUE}🧪 Testing act installation...${NC}"
if act --list >/dev/null 2>&1; then
    echo -e "${GREEN}✅ act is working correctly${NC}"
else
    echo -e "${RED}❌ act test failed${NC}"
    exit 1
fi

echo -e "\n${GREEN}🎉 act setup completed!${NC}"
echo -e "\n${BLUE}Usage:${NC}"
echo -e "  ${YELLOW}make act-ci${NC}        # Run CI workflow locally"
echo -e "  ${YELLOW}make act-pipeline${NC}   # Run pipeline workflow locally"
echo -e "  ${YELLOW}act -l${NC}              # List available workflows"
echo -e "  ${YELLOW}act -W .github/workflows/ci.yml${NC}  # Run specific workflow"
