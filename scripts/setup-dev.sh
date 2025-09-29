#!/bin/bash

# Simplified development setup script for meal expense tracker
# TIGER-style: Safety, Performance, Developer Experience

set -euo pipefail

# =============================================================================
# CONSTANTS AND CONFIGURATION
# =============================================================================

readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
readonly SCRIPT_NAME="$(basename "${BASH_SOURCE[0]}")"

# Tool versions
readonly PYTHON_VERSION="3.13"
readonly NODE_VERSION="22"

# Colors for output
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly RED='\033[0;31m'
readonly BLUE='\033[0;34m'
readonly NC='\033[0m' # No Color

# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

log_info() {
  echo -e "${GREEN}[INFO]${NC} $*" >&2
}

log_warn() {
  echo -e "${YELLOW}[WARN]${NC} $*" >&2
}

log_error() {
  echo -e "${RED}[ERROR]${NC} $*" >&2
}

log_section() {
  echo -e "\n${GREEN}=== $* ===${NC}"
}

# Show usage information
show_usage() {
  cat << EOF
Usage: $SCRIPT_NAME [OPTIONS]

Simplified development setup script for meal expense tracker.

OPTIONS:
    -m, --mode MODE       Setup mode (default: full)
                         MODES:
                           full          - Complete development setup
                           minimal       - Minimal setup (Python only)
                           tools         - Install system tools only
                           optional      - Install optional development tools
                           upgrade       - Upgrade all development tools
                           debug         - Analyze system without changes

    -s, --start           Start application after setup
    -d, --debug           Enable debug output
    -h, --help            Show this help message

EXAMPLES:
    $SCRIPT_NAME                    # Full development setup
    $SCRIPT_NAME --mode minimal     # Minimal Python setup
    $SCRIPT_NAME --mode tools       # Install system tools
    $SCRIPT_NAME --mode optional    # Install optional development tools
    $SCRIPT_NAME --mode upgrade     # Upgrade all development tools
    $SCRIPT_NAME --start            # Setup and start application

DESCRIPTION:
    This script provides a simplified setup process for development:

    • full (default): Complete development environment
    • minimal: Python environment only
    • tools: System tools installation
    • optional: Optional development tools (Docker, Terraform, AWS CLI, act, Playwright)
    • upgrade: Upgrade all development tools to latest versions
    • debug: System analysis without changes
EOF
}

# =============================================================================
# SYSTEM CHECKS
# =============================================================================

check_python() {
  if command -v python3 >/dev/null 2>&1; then
    local version
    version=$(python3 --version 2>&1 | cut -d' ' -f2 | cut -d'.' -f1,2)
    if [[ "$version" == "$PYTHON_VERSION" ]]; then
      log_info "Python $PYTHON_VERSION found"
      return 0
    else
      log_warn "Python $version found, but $PYTHON_VERSION recommended"
      return 1
    fi
  else
    log_error "Python 3 not found"
    return 1
  fi
}

check_node() {
  if command -v node >/dev/null 2>&1; then
    local version
    version=$(node --version 2>&1 | cut -d'v' -f2 | cut -d'.' -f1)
    if [[ "$version" == "$NODE_VERSION" ]]; then
      log_info "Node.js $NODE_VERSION found"
      return 0
    else
      log_warn "Node.js $version found, but $NODE_VERSION recommended"
      return 1
    fi
  else
    log_warn "Node.js not found (optional for frontend development)"
    return 1
  fi
}

check_system_tools() {
  local missing_tools=()

  # Essential tools
  for tool in git make curl; do
    if ! command -v "$tool" >/dev/null 2>&1; then
      missing_tools+=("$tool")
    fi
  done

  # Optional tools
  for tool in docker terraform aws node npm npx act; do
    if ! command -v "$tool" >/dev/null 2>&1; then
      log_warn "$tool not found (optional)"
    fi
  done

  if [[ ${#missing_tools[@]} -gt 0 ]]; then
    log_error "Missing essential tools: ${missing_tools[*]}"
    return 1
  fi

  log_info "System tools check passed"
  return 0
}

# =============================================================================
# SETUP FUNCTIONS
# =============================================================================

setup_python_environment() {
  log_section "Setting up Python environment"

  cd "$PROJECT_ROOT"

  # Create virtual environment if it doesn't exist
  if [[ ! -d "venv" ]]; then
    log_info "Creating Python virtual environment..."
    python3 -m venv venv
  else
    log_info "Virtual environment already exists"
  fi

  # Activate virtual environment
  source venv/bin/activate

  # Upgrade pip
  log_info "Upgrading pip..."
  pip install --upgrade pip

  # Generate and install requirements using Makefile
  if [[ -f "Makefile" ]]; then
    log_info "Generating requirements files..."
    make requirements
  fi

  if [[ -f "requirements.txt" ]]; then
    log_info "Installing Python requirements..."
    pip install -r requirements.txt
  else
    log_warn "requirements.txt not found"
    return 1
  fi

  # Install development requirements if they exist
  if [[ -f "requirements-dev.txt" ]]; then
    log_info "Installing development requirements..."
    pip install -r requirements-dev.txt
  fi

  log_info "Python environment setup complete"
}

setup_database() {
  log_section "Setting up database"

  cd "$PROJECT_ROOT"
  source venv/bin/activate

  # Run database migrations
  if command -v flask >/dev/null 2>&1; then
    log_info "Running database migrations..."
    flask db upgrade || log_warn "Database migration failed (may not be configured)"
  else
    log_warn "Flask not found, skipping database setup"
  fi

  log_info "Database setup complete"
}

install_system_tools() {
  log_section "Installing system tools"

  # Detect package manager
  if command -v apt-get >/dev/null 2>&1; then
    log_info "Installing tools with apt-get..."
    sudo apt-get update
    sudo apt-get install -y git make curl build-essential
  elif command -v yum >/dev/null 2>&1; then
    log_info "Installing tools with yum..."
    sudo yum install -y git make curl gcc gcc-c++ make
  elif command -v brew >/dev/null 2>&1; then
    log_info "Installing tools with Homebrew..."
    brew install git make curl
  else
    log_warn "No supported package manager found"
    return 1
  fi

  log_info "System tools installation complete"
}

setup_node_environment() {
  log_section "Setting up Node.js environment"

  if ! command -v node >/dev/null 2>&1; then
    log_warn "Node.js not found, skipping Node.js setup"
    return 0
  fi

  # Install npm dependencies if package.json exists
  if [[ -f "package.json" ]]; then
    log_info "Installing npm dependencies..."
    npm install
  else
    log_warn "package.json not found, skipping npm setup"
  fi

  log_info "Node.js environment setup complete"
}

install_docker() {
  log_section "Installing Docker"

  if command -v docker >/dev/null 2>&1; then
    log_info "Docker already installed"
    return 0
  fi

  # Detect package manager and install Docker
  if command -v apt-get >/dev/null 2>&1; then
    log_info "Installing Docker with apt-get..."
    sudo apt-get update
    sudo apt-get install -y ca-certificates curl gnupg lsb-release
    sudo mkdir -p /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
    sudo apt-get update
    sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
  elif command -v yum >/dev/null 2>&1; then
    log_info "Installing Docker with yum..."
    sudo yum install -y yum-utils
    sudo yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
    sudo yum install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
  elif command -v brew >/dev/null 2>&1; then
    log_info "Installing Docker with Homebrew..."
    brew install --cask docker
  else
    log_warn "No supported package manager found for Docker installation"
    return 1
  fi

  # Start Docker service
  if command -v systemctl >/dev/null 2>&1; then
    sudo systemctl start docker
    sudo systemctl enable docker
  fi

  # Add user to docker group
  sudo usermod -aG docker "$USER"

  log_info "Docker installation complete"
  log_warn "Please log out and back in for Docker group changes to take effect"
}

install_terraform() {
  log_section "Installing Terraform"

  if command -v terraform >/dev/null 2>&1; then
    log_info "Terraform already installed"
    return 0
  fi

  # Download and install Terraform
  local terraform_version="1.6.6"
  local arch=$(uname -m)

  case "$arch" in
    x86_64) arch="amd64" ;;
    aarch64|arm64) arch="arm64" ;;
    *) log_error "Unsupported architecture: $arch"; return 1 ;;
  esac

  log_info "Installing Terraform $terraform_version for $arch..."

  # Create local bin directory if it doesn't exist
  mkdir -p "$HOME/.local/bin"

  # Download and install
  curl -fsSL "https://releases.hashicorp.com/terraform/${terraform_version}/terraform_${terraform_version}_linux_${arch}.zip" -o /tmp/terraform.zip
  unzip -q /tmp/terraform.zip -d /tmp
  mv /tmp/terraform "$HOME/.local/bin/"
  chmod +x "$HOME/.local/bin/terraform"
  rm /tmp/terraform.zip

  # Add to PATH if not already there
  if ! echo "$PATH" | grep -q "$HOME/.local/bin"; then
    echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME/.bashrc"
    echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME/.zshrc"
    log_warn "Added $HOME/.local/bin to PATH. Please restart your shell or run: source ~/.bashrc"
  fi

  log_info "Terraform installation complete"
}

install_aws_cli() {
  log_section "Installing AWS CLI"

  if command -v aws >/dev/null 2>&1; then
    log_info "AWS CLI already installed"
    return 0
  fi

  # Create local bin directory if it doesn't exist
  mkdir -p "$HOME/.local/bin"

  # Download and install AWS CLI v2
  log_info "Installing AWS CLI v2..."
  curl -fsSL "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o /tmp/awscliv2.zip
  unzip -q /tmp/awscliv2.zip -d /tmp
  /tmp/aws/install --install-dir "$HOME/.local/aws-cli" --bin-dir "$HOME/.local/bin"
  rm -rf /tmp/aws /tmp/awscliv2.zip

  # Add to PATH if not already there
  if ! echo "$PATH" | grep -q "$HOME/.local/bin"; then
    echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME/.bashrc"
    echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME/.zshrc"
    log_warn "Added $HOME/.local/bin to PATH. Please restart your shell or run: source ~/.bashrc"
  fi

  log_info "AWS CLI installation complete"
}

install_act() {
  log_section "Installing act (GitHub Actions Local Runner)"

  if command -v act >/dev/null 2>&1; then
    log_info "act already installed"
    return 0
  fi

  # Create local bin directory if it doesn't exist
  mkdir -p "$HOME/.local/bin"

  # Download and install act
  log_info "Installing act..."
  curl -fsSL https://raw.githubusercontent.com/nektos/act/master/install.sh | bash -s -- -b "$HOME/.local/bin"

  # Add to PATH if not already there
  if ! echo "$PATH" | grep -q "$HOME/.local/bin"; then
    echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME/.bashrc"
    echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME/.zshrc"
    log_warn "Added $HOME/.local/bin to PATH. Please restart your shell or run: source ~/.bashrc"
  fi

  log_info "act installation complete"
}

install_playwright() {
  log_section "Installing Playwright"

  if ! command -v node >/dev/null 2>&1; then
    log_warn "Node.js not found, skipping Playwright installation"
    return 1
  fi

  if ! command -v npm >/dev/null 2>&1; then
    log_warn "npm not found, skipping Playwright installation"
    return 1
  fi

  # Install Playwright
  log_info "Installing Playwright..."
  npm install -g @playwright/test
  npx playwright install

  log_info "Playwright installation complete"
}

# =============================================================================
# UPGRADE FUNCTIONS
# =============================================================================

upgrade_node() {
  log_section "Upgrading Node.js"

  if ! command -v node >/dev/null 2>&1; then
    log_warn "Node.js not found, installing instead..."
    install_node
    return $?
  fi

  local current_version
  current_version=$(node --version 2>&1 | cut -d'v' -f2 | cut -d'.' -f1)

  if [[ "$current_version" -ge "$NODE_VERSION" ]]; then
    log_info "Node.js $current_version is already up to date (>= $NODE_VERSION)"
    return 0
  fi

  log_info "Upgrading Node.js from v$current_version to v$NODE_VERSION..."

  # Detect package manager and upgrade
  if command -v apt-get >/dev/null 2>&1; then
    log_info "Upgrading Node.js with apt-get..."
    curl -fsSL https://deb.nodesource.com/setup_${NODE_VERSION}.x | sudo -E bash -
    sudo apt-get install -y nodejs
  elif command -v yum >/dev/null 2>&1; then
    log_info "Upgrading Node.js with yum..."
    curl -fsSL https://rpm.nodesource.com/setup_${NODE_VERSION}.x | sudo bash -
    sudo yum install -y nodejs npm
  elif command -v brew >/dev/null 2>&1; then
    log_info "Upgrading Node.js with Homebrew..."
    brew upgrade node
  else
    log_warn "No supported package manager found for Node.js upgrade"
    return 1
  fi

  log_info "Node.js upgrade complete"
}

upgrade_python() {
  log_section "Upgrading Python"

  if ! command -v python3 >/dev/null 2>&1; then
    log_warn "Python3 not found, cannot upgrade"
    return 1
  fi

  local current_version
  current_version=$(python3 --version 2>&1 | cut -d' ' -f2 | cut -d'.' -f1,2)

  if [[ "$current_version" == "$PYTHON_VERSION" ]]; then
    log_info "Python $current_version is already up to date"
    return 0
  fi

  log_info "Current Python version: $current_version, target: $PYTHON_VERSION"
  log_warn "Python upgrade requires system-level changes and may affect other applications"
  log_warn "Consider using pyenv for Python version management instead"

  # Detect package manager and upgrade
  if command -v apt-get >/dev/null 2>&1; then
    log_info "Upgrading Python with apt-get..."
    sudo apt-get update
    sudo apt-get install -y python${PYTHON_VERSION} python${PYTHON_VERSION}-venv python${PYTHON_VERSION}-pip
  elif command -v yum >/dev/null 2>&1; then
    log_info "Upgrading Python with yum..."
    sudo yum install -y python${PYTHON_VERSION} python${PYTHON_VERSION}-pip
  elif command -v brew >/dev/null 2>&1; then
    log_info "Upgrading Python with Homebrew..."
    brew upgrade python@${PYTHON_VERSION}
  else
    log_warn "No supported package manager found for Python upgrade"
    return 1
  fi

  log_info "Python upgrade complete"
}

upgrade_docker() {
  log_section "Upgrading Docker"

  if ! command -v docker >/dev/null 2>&1; then
    log_warn "Docker not found, installing instead..."
    install_docker
    return $?
  fi

  log_info "Upgrading Docker to latest version..."

  # Detect package manager and upgrade
  if command -v apt-get >/dev/null 2>&1; then
    log_info "Upgrading Docker with apt-get..."
    sudo apt-get update
    sudo apt-get upgrade -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
  elif command -v yum >/dev/null 2>&1; then
    log_info "Upgrading Docker with yum..."
    sudo yum update -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
  elif command -v brew >/dev/null 2>&1; then
    log_info "Upgrading Docker with Homebrew..."
    brew upgrade --cask docker
  else
    log_warn "No supported package manager found for Docker upgrade"
    return 1
  fi

  # Restart Docker service
  if command -v systemctl >/dev/null 2>&1; then
    sudo systemctl restart docker
  fi

  log_info "Docker upgrade complete"
}

upgrade_terraform() {
  log_section "Upgrading Terraform"

  if ! command -v terraform >/dev/null 2>&1; then
    log_warn "Terraform not found, installing instead..."
    install_terraform
    return $?
  fi

  local current_version
  current_version=$(terraform --version 2>&1 | head -n1 | cut -d'v' -f2)
  local target_version="1.6.6"

  if [[ "$current_version" == "$target_version" ]]; then
    log_info "Terraform $current_version is already up to date"
    return 0
  fi

  log_info "Upgrading Terraform from v$current_version to v$target_version..."

  # Download and install latest version
  local arch=$(uname -m)
  case "$arch" in
    x86_64) arch="amd64" ;;
    aarch64|arm64) arch="arm64" ;;
    *) log_error "Unsupported architecture: $arch"; return 1 ;;
  esac

  # Create local bin directory if it doesn't exist
  mkdir -p "$HOME/.local/bin"

  # Download and install
  curl -fsSL "https://releases.hashicorp.com/terraform/${target_version}/terraform_${target_version}_linux_${arch}.zip" -o /tmp/terraform.zip
  unzip -q /tmp/terraform.zip -d /tmp
  mv /tmp/terraform "$HOME/.local/bin/"
  chmod +x "$HOME/.local/bin/terraform"
  rm /tmp/terraform.zip

  log_info "Terraform upgrade complete"
}

upgrade_aws_cli() {
  log_section "Upgrading AWS CLI"

  if ! command -v aws >/dev/null 2>&1; then
    log_warn "AWS CLI not found, installing instead..."
    install_aws_cli
    return $?
  fi

  log_info "Upgrading AWS CLI to latest version..."

  # Create local bin directory if it doesn't exist
  mkdir -p "$HOME/.local/bin"

  # Download and install latest AWS CLI v2
  curl -fsSL "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o /tmp/awscliv2.zip
  unzip -q /tmp/awscliv2.zip -d /tmp
  /tmp/aws/install --install-dir "$HOME/.local/aws-cli" --bin-dir "$HOME/.local/bin" --update
  rm -rf /tmp/aws /tmp/awscliv2.zip

  log_info "AWS CLI upgrade complete"
}

upgrade_act() {
  log_section "Upgrading act"

  if ! command -v act >/dev/null 2>&1; then
    log_warn "act not found, installing instead..."
    install_act
    return $?
  fi

  log_info "Upgrading act to latest version..."

  # Create local bin directory if it doesn't exist
  mkdir -p "$HOME/.local/bin"

  # Download and install latest act
  curl -fsSL https://raw.githubusercontent.com/nektos/act/master/install.sh | bash -s -- -b "$HOME/.local/bin"

  log_info "act upgrade complete"
}

upgrade_playwright() {
  log_section "Upgrading Playwright"

  if ! command -v node >/dev/null 2>&1; then
    log_warn "Node.js not found, skipping Playwright upgrade"
    return 1
  fi

  if ! command -v npm >/dev/null 2>&1; then
    log_warn "npm not found, skipping Playwright upgrade"
    return 1
  fi

  log_info "Upgrading Playwright to latest version..."

  # Upgrade Playwright
  npm install -g @playwright/test@latest
  npx playwright install

  log_info "Playwright upgrade complete"
}

# =============================================================================
# MODE FUNCTIONS
# =============================================================================

run_full_mode() {
  log_info "🚀 Full mode: Complete development setup"

  check_python || log_warn "Python check failed"
  check_node || log_warn "Node.js check failed"
  check_system_tools || log_warn "System tools check failed"

  setup_python_environment
  setup_node_environment
  setup_database

  log_info "✅ Full development setup complete"
}

run_minimal_mode() {
  log_info "🔧 Minimal mode: Python environment only"

  check_python || {
    log_error "Python is required for minimal setup"
    exit 1
  }

  setup_python_environment

  log_info "✅ Minimal setup complete"
}

run_tools_mode() {
  log_info "🔧 Tools mode: System tools installation"

  install_system_tools

  log_info "✅ System tools installation complete"
}

run_optional_tools_mode() {
  log_info "🛠️  Optional tools mode: Installing development tools"

  # Install optional tools
  install_docker
  install_terraform
  install_aws_cli
  install_act
  install_playwright

  log_info "✅ Optional tools installation complete"
}

run_upgrade_mode() {
  log_info "⬆️  Upgrade mode: Upgrading development tools"

  # Upgrade all tools
  upgrade_node
  upgrade_python
  upgrade_docker
  upgrade_terraform
  upgrade_aws_cli
  upgrade_act
  upgrade_playwright

  log_info "✅ Tool upgrades complete"
}

run_debug_mode() {
  log_info "🔍 Debug mode: System analysis"

  echo -e "\n${BLUE}=== System Information ===${NC}"
  echo "OS: $(uname -s)"
  echo "Architecture: $(uname -m)"
  echo "Shell: $SHELL"

  echo -e "\n${BLUE}=== Tool Versions ===${NC}"
  check_python && echo "Python: $(python3 --version 2>&1)"
  check_node && echo "Node.js: $(node --version 2>&1)"
  check_system_tools

  echo -e "\n${BLUE}=== Project Status ===${NC}"
  cd "$PROJECT_ROOT"
  if [[ -d "venv" ]]; then
    echo "Virtual environment: ✅ Found"
  else
    echo "Virtual environment: ❌ Not found"
  fi

  if [[ -f "requirements.txt" ]]; then
    echo "Requirements: ✅ Found"
  else
    echo "Requirements: ❌ Not found"
  fi

  if [[ -f "package.json" ]]; then
    echo "package.json: ✅ Found"
    if [[ -d "node_modules" ]]; then
      echo "node_modules: ✅ Found"
    else
      echo "node_modules: ❌ Not found"
    fi
  else
    echo "package.json: ❌ Not found"
  fi

  if [[ -f "Makefile" ]]; then
    echo "Makefile: ✅ Found"
  else
    echo "Makefile: ❌ Not found"
  fi

  if [[ -f "Dockerfile" ]]; then
    echo "Dockerfile: ✅ Found"
  else
    echo "Dockerfile: ❌ Not found"
  fi

  if [[ -f "docker-compose.yml" ]]; then
    echo "docker-compose.yml: ✅ Found"
  else
    echo "docker-compose.yml: ❌ Not found"
  fi

  log_info "Debug analysis complete"
}

# =============================================================================
# MAIN EXECUTION
# =============================================================================

main() {
  local mode="full"
  local start_app=false
  local debug=false

  # Parse command line arguments
  while [[ $# -gt 0 ]]; do
    case $1 in
      -m|--mode)
        mode="$2"
        shift 2
        ;;
      -s|--start)
        start_app=true
        shift
        ;;
      -d|--debug)
        debug=true
        shift
        ;;
      -h|--help)
        show_usage
        exit 0
        ;;
      *)
        log_error "Unknown option: $1"
        show_usage
        exit 1
        ;;
    esac
  done

  # Validate mode
  case "$mode" in
    full|minimal|tools|optional|upgrade|debug)
      ;;
    *)
      log_error "Invalid mode: $mode"
      show_usage
      exit 1
      ;;
  esac

  # Set debug mode
  if [[ "$debug" == "true" ]]; then
    set -x
  fi

  log_info "Starting $SCRIPT_NAME in $mode mode"

  # Execute based on mode
  case "$mode" in
    full)
      run_full_mode
      ;;
    minimal)
      run_minimal_mode
      ;;
    tools)
      run_tools_mode
      ;;
    optional)
      run_optional_tools_mode
      ;;
    upgrade)
      run_upgrade_mode
      ;;
    debug)
      run_debug_mode
      ;;
  esac

  # Start application if requested
  if [[ "$start_app" == "true" ]]; then
    log_section "Starting application"
    cd "$PROJECT_ROOT"
    source venv/bin/activate
    make run
  fi

  log_info "Setup complete!"
}

# Run main function
main "$@"
