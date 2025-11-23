#!/bin/bash

# Agent Shell Initialization Script
# This script sets up the shell environment for AI agents and switches to bash if needed

set -euo pipefail

# Get script directory and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Check current shell
CURRENT_SHELL=$(basename "$SHELL")
log_info "Current shell: $CURRENT_SHELL"

# If not bash, switch to bash
if [[ "$CURRENT_SHELL" != "bash" ]]; then
    log_info "Switching to bash for better compatibility..."
    exec bash --init-file "$PROJECT_ROOT/.agent_profile"
else
    log_success "Already using bash"
    source "$PROJECT_ROOT/.agent_profile"
fi
