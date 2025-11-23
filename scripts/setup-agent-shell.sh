#!/bin/bash

# Agent Shell Setup Script
# This script configures the shell environment properly for AI agents

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

log_info "Setting up agent shell environment..."

# 1. Set proper terminal type
export TERM=xterm-256color
log_success "Terminal type set to xterm-256color"

# 2. Clean and set PATH
export PATH="/usr/local/bin:/usr/bin:/bin:/usr/local/sbin:/usr/sbin:/sbin:/home/mtd37/.local/bin:/home/mtd37/bin"
log_success "PATH cleaned and set"

# 3. Set project root
export PROJECT_ROOT="$PROJECT_ROOT"
cd "$PROJECT_ROOT"
log_success "Working directory set to: $PROJECT_ROOT"

# 4. Activate virtual environment if it exists
if [[ -d "venv" ]]; then
    source venv/bin/activate
    log_success "Virtual environment activated"
else
    log_warning "Virtual environment not found, using system Python"
fi

# 5. Set environment variables
export PYTHONPATH="$PROJECT_ROOT:${PYTHONPATH:-}"
export FLASK_APP=wsgi:app
export FLASK_ENV=development

# 6. Check essential tools
log_info "Checking essential tools..."

tools=("python3" "pip3" "git" "make")
missing_tools=()

for tool in "${tools[@]}"; do
    if command -v "$tool" >/dev/null 2>&1; then
        log_success "$tool found: $(which "$tool")"
    else
        log_error "$tool not found"
        missing_tools+=("$tool")
    fi
done

# 7. Check AWS CLI
if command -v aws >/dev/null 2>&1; then
    log_success "AWS CLI found: $(which aws)"

    # Check AWS configuration
    if aws sts get-caller-identity >/dev/null 2>&1; then
        log_success "AWS credentials configured"
    else
        log_warning "AWS credentials not configured"
        log_info "Run 'aws configure' to set up credentials"
    fi
else
    log_warning "AWS CLI not found"
fi

# 8. Check Node.js and npm
if command -v node >/dev/null 2>&1; then
    log_success "Node.js found: $(node --version)"
else
    log_warning "Node.js not found"
fi

if command -v npm >/dev/null 2>&1; then
    log_success "npm found: $(npm --version)"
else
    log_warning "npm not found"
fi

# 9. Check Docker
if command -v docker >/dev/null 2>&1; then
    log_success "Docker found: $(which docker)"
else
    log_warning "Docker not found"
fi

# 10. Summary
echo ""
log_info "Shell setup summary:"
echo "  - Working directory: $PROJECT_ROOT"
echo "  - Python: $(which python)"
echo "  - Terminal: $TERM"
echo "  - Virtual env: $(if [[ -n "${VIRTUAL_ENV:-}" ]]; then echo "Active ($VIRTUAL_ENV)"; else echo "Not active"; fi)"

if [[ ${#missing_tools[@]} -gt 0 ]]; then
    log_warning "Missing tools: ${missing_tools[*]}"
    log_info "Install missing tools with: sudo apt-get update && sudo apt-get install ${missing_tools[*]}"
fi

# 11. Test basic functionality
log_info "Testing shell functionality..."

# Test Python
if python -c "import sys; print('Python version:', sys.version)" >/dev/null 2>&1; then
    log_success "Python import test passed"
else
    log_error "Python import test failed"
fi

# Test git
if git status >/dev/null 2>&1; then
    log_success "Git repository test passed"
else
    log_warning "Git repository test failed or not in a git repo"
fi

log_success "Agent shell setup complete!"
echo ""
log_info "Available commands:"
echo "  - make help          # Show available make targets"
echo "  - python app.py      # Run the Flask application"
echo "  - aws --version      # Check AWS CLI"
echo "  - docker --version   # Check Docker"
echo "  - npm test           # Run tests"
