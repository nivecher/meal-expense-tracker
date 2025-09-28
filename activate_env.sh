#!/bin/bash
# Meal Expense Tracker Development Environment Activation Script
# This script ensures the virtual environment is always activated

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Activating Meal Expense Tracker Development Environment...${NC}"

# Navigate to project directory
cd /home/mtd37/workspace/meal-expense-tracker

# Activate virtual environment
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
    echo -e "${GREEN}✅ Virtual environment activated successfully!${NC}"
    echo -e "${GREEN}📍 Current directory: $(pwd)${NC}"
    echo -e "${GREEN}🐍 Python version: $(python --version)${NC}"
    echo -e "${GREEN}📦 Pip location: $(which pip)${NC}"
    echo ""
    echo -e "${BLUE}🛠️  Available commands:${NC}"
    echo "  flask run           - Start development server"
    echo "  python -m pytest   - Run tests"
    echo "  make lint          - Run linters"
    echo "  make test          - Run full test suite"
    echo ""
else
    echo "❌ Virtual environment not found! Please run: python -m venv venv"
fi
