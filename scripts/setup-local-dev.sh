#!/bin/bash

# Unified setup script for meal expense tracker
# TIGER-style: Safety, Performance, Developer Experience + SOLID principles

set -euo pipefail

# =============================================================================
# CONSTANTS AND CONFIGURATION
# =============================================================================

readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
readonly SCRIPT_NAME="$(basename "${BASH_SOURCE[0]}")"
readonly MAX_RETRIES=3
readonly DOWNLOAD_TIMEOUT_SEC=30
readonly MAX_PACKAGES_PER_BATCH=20

# Tool versions (centralized configuration)
readonly TERRAFORM_VERSION="1.6.6"
readonly PYTHON_VERSION="3.13"
readonly NODE_VERSION="22"

# Colors for output
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly RED='\033[0;31m'
readonly BLUE='\033[0;34m'
readonly NC='\033[0m' # No Color

# =============================================================================
# UTILITY FUNCTIONS (Pure, Testable)
# =============================================================================

# Safe logging with consistent formatting
log_info() {
  echo -e "${GREEN}[INFO]${NC} $*" >&2
}

log_warn() {
  echo -e "${YELLOW}[WARN]${NC} $*" >&2
}

log_error() {
  echo -e "${RED}[ERROR]${NC} $*" >&2
}

log_debug() {
  if [[ "${DEBUG:-}" == "true" ]]; then
    echo -e "${BLUE}[DEBUG]${NC} $*" >&2
  fi
}

log_section() {
  echo -e "\n${GREEN}=== $* ===${NC}"
}

# Show usage information
show_usage() {
  cat << EOF
Usage: $SCRIPT_NAME [OPTIONS]

Unified setup script for meal expense tracker development environment.

OPTIONS:
    -m, --mode MODE       Setup mode (default: auto)
                         MODES:
                           auto     - Detect and install missing components
                           full     - Full setup with all tools (requires sudo)
                           minimal  - Minimal setup without sudo operations
                           debug    - Analyze system without making changes
                           python   - Python environment only
                           tools    - Install system tools only
                           act      - Setup ACT (GitHub Actions) environment
                           start    - Start application only

    -s, --start           Start application after setup
    -d, --debug           Enable debug output
    -h, --help            Show this help message
    --skip-deps           Skip dependency installation
    --skip-python         Skip Python environment setup
    --skip-tools          Skip system tools installation
    --skip-act            Skip ACT environment setup
    --skip-init           Skip project initialization

EXAMPLES:
    $SCRIPT_NAME                    # Auto-detect and setup missing components
    $SCRIPT_NAME --mode full        # Full setup with all tools (sudo required)
    $SCRIPT_NAME --mode minimal     # Minimal setup without sudo
    $SCRIPT_NAME --mode debug       # Analyze system status
    $SCRIPT_NAME --mode python      # Setup Python environment only
    $SCRIPT_NAME --start            # Setup and start application
    $SCRIPT_NAME --mode minimal --start  # Minimal setup and start

DESCRIPTION:
    This script provides multiple setup modes for different use cases:

    • auto (default): Intelligently detects what's needed and installs it
    • full: Complete setup with all system tools (requires sudo)
    • minimal: User-space setup without system modifications
    • debug: Analyzes system without making changes
    • python: Python environment and dependencies only
    • tools: System tools installation only
    • act: GitHub Actions local runner setup
    • start: Application startup only

    The script is idempotent and can be run multiple times safely.

EOF
}

# Parse command line arguments
parse_arguments() {
  local mode="auto"
  local start_app=false
  local skip_deps=false
  local skip_python=false
  local skip_tools=false
  local skip_act=false
  local skip_init=false

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
        DEBUG="true"
        shift
        ;;
      -h|--help)
        show_usage
        exit 0
        ;;
      --skip-deps)
        skip_deps=true
        shift
        ;;
      --skip-python)
        skip_python=true
        shift
        ;;
      --skip-tools)
        skip_tools=true
        shift
        ;;
      --skip-act)
        skip_act=true
        shift
        ;;
      --skip-init)
        skip_init=true
        shift
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
    auto|full|minimal|debug|python|tools|act|start)
      ;;
    *)
      log_error "Invalid mode: $mode"
      show_usage
      exit 1
      ;;
  esac

  # Export configuration
  export SETUP_MODE="$mode"
  export START_APP="$start_app"
  export SKIP_DEPS="$skip_deps"
  export SKIP_PYTHON="$skip_python"
  export SKIP_TOOLS="$skip_tools"
  export SKIP_ACT="$skip_act"
  export SKIP_INIT="$skip_init"
}

# Validate input parameters with bounds
validate_package_list() {
  local -r packages=("$@")
  local -r count=${#packages[@]}

  if [[ $count -eq 0 ]]; then
    log_error "Package list cannot be empty"
    return 1
  fi

  if [[ $count -gt $MAX_PACKAGES_PER_BATCH ]]; then
    log_error "Too many packages in single batch (max: $MAX_PACKAGES_PER_BATCH)"
    return 1
  fi

  return 0
}

# Detect package manager (pure function)
detect_package_manager() {
  if command -v apt-get >/dev/null 2>&1; then
    echo "apt"
  elif command -v yum >/dev/null 2>&1; then
    echo "yum"
  elif command -v dnf >/dev/null 2>&1; then
    echo "dnf"
  elif command -v brew >/dev/null 2>&1; then
    echo "brew"
  else
    echo "unknown"
  fi
}

# Check if command exists with timeout
command_exists_with_timeout() {
  local -r cmd="$1"
  local -r timeout_sec="${2:-5}"

  timeout "$timeout_sec" command -v "$cmd" >/dev/null 2>&1
}

# Check if command exists
command_exists() {
  local -r cmd="$1"
  command -v "$cmd" >/dev/null 2>&1
}

# =============================================================================
# PACKAGE MANAGEMENT (Single Responsibility)
# =============================================================================

# Install packages with validation and batching (idempotent)
install_packages_batch() {
  local -r packages=("$@")

  if ! validate_package_list "${packages[@]}"; then
    return 1
  fi

  local -r pkg_mgr="$(detect_package_manager)"

  case "$pkg_mgr" in
    "apt")
      sudo apt-get update
      # Use --fix-missing to handle broken dependencies gracefully
      sudo apt-get install -y --fix-missing "${packages[@]}" || {
        log_warn "Some packages failed to install, continuing..."
        return 0
      }
      ;;
    "yum")
      sudo yum install -y "${packages[@]}" || {
        log_warn "Some packages failed to install, continuing..."
        return 0
      }
      ;;
    "dnf")
      sudo dnf install -y "${packages[@]}" || {
        log_warn "Some packages failed to install, continuing..."
        return 0
      }
      ;;
    "brew")
      brew install "${packages[@]}" || {
        log_warn "Some packages failed to install, continuing..."
        return 0
      }
      ;;
    *)
      log_error "Unsupported package manager: $pkg_mgr"
      return 1
      ;;
  esac
}

# =============================================================================
# TOOL INSTALLATION (Interface Segregation)
# =============================================================================

# Base tool installer interface
install_tool_if_missing() {
  local -r tool_name="$1"
  local -r install_func="$2"
  local -r version_flag="${3:---version}"

  if command_exists_with_timeout "$tool_name"; then
    log_info "$tool_name is already installed"
    "$tool_name" $version_flag 2>/dev/null || true
    return 0
  fi

  log_info "Installing $tool_name..."
  if "$install_func"; then
    log_info "$tool_name installed successfully"
    "$tool_name" $version_flag 2>/dev/null || true
  else
    log_error "Failed to install $tool_name"
    return 1
  fi
}

# Terraform installation (single responsibility)
install_terraform_impl() {
  local -r pkg_mgr="$(detect_package_manager)"
  local tmp_dir
  tmp_dir="$(mktemp -d)"

  # Cleanup on exit
  trap "rm -rf '$tmp_dir'" EXIT

  case "$pkg_mgr" in
    "apt")
      # Check if HashiCorp repository is already configured
      if [[ ! -f /etc/apt/sources.list.d/hashicorp.list ]] || ! grep -q "apt.releases.hashicorp.com" /etc/apt/sources.list.d/hashicorp.list; then
        # Only add GPG key if keyring doesn't exist
        if [[ ! -f /usr/share/keyrings/hashicorp-archive-keyring.gpg ]]; then
          wget -qO- https://apt.releases.hashicorp.com/gpg | \
            sudo gpg --dearmor -o /usr/share/keyrings/hashicorp-archive-keyring.gpg
        fi
        echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $(lsb_release -cs) main" | \
          sudo tee /etc/apt/sources.list.d/hashicorp.list
    sudo apt-get update
      fi
    sudo apt-get install -y terraform
      ;;
    "yum")
    sudo yum install -y yum-utils
      # Check if repo already exists
      if ! sudo yum-config-manager --list-repos | grep -q "hashicorp"; then
    sudo yum-config-manager --add-repo https://rpm.releases.hashicorp.com/RHEL/hashicorp.repo
      fi
    sudo yum -y install terraform
      ;;
    "dnf")
    sudo dnf install -y dnf-plugins-core
      # Check if repo already exists
      if ! sudo dnf config-manager --list-repos | grep -q "hashicorp"; then
    sudo dnf config-manager --add-repo https://rpm.releases.hashicorp.com/fedora/hashicorp.repo
      fi
    sudo dnf -y install terraform
      ;;
    "brew")
    brew tap hashicorp/tap
    brew install hashicorp/tap/terraform
      ;;
    *)
    # Fallback to manual installation
      local -r os_arch
      os_arch="$(uname -s | tr '[:upper:]' '[:lower:]')_$(uname -m | sed 's/x86_64/amd64/')"
      local -r tf_url="https://releases.hashicorp.com/terraform/${TERRAFORM_VERSION}/terraform_${TERRAFORM_VERSION}_${os_arch}.zip"

      wget -q --timeout="$DOWNLOAD_TIMEOUT_SEC" --tries=3 "$tf_url" -O "${tmp_dir}/terraform.zip"
    unzip -o "${tmp_dir}/terraform.zip" -d "${tmp_dir}"
    sudo install -o root -g root -m 0755 "${tmp_dir}/terraform" /usr/local/bin/terraform
      ;;
  esac
}

# Trivy installation (single responsibility)
install_trivy_impl() {
  local -r pkg_mgr="$(detect_package_manager)"

  case "$pkg_mgr" in
    "apt")
      sudo apt-get install -y wget apt-transport-https gnupg lsb-release

      # Check if Trivy repo already exists to avoid duplicates
      if [[ ! -f /etc/apt/sources.list.d/trivy.list ]] || ! grep -q "aquasecurity.github.io/trivy-repo" /etc/apt/sources.list.d/trivy.list; then
        wget -qO - https://aquasecurity.github.io/trivy-repo/deb/public.key | \
          gpg --dearmor | sudo tee /usr/share/keyrings/trivy.gpg >/dev/null
        echo "deb [signed-by=/usr/share/keyrings/trivy.gpg] https://aquasecurity.github.io/trivy-repo/deb $(lsb_release -sc) main" | \
          sudo tee /etc/apt/sources.list.d/trivy.list
        sudo apt-get update
      fi
      sudo apt-get install -y trivy
      ;;
    "yum")
      sudo yum install -y yum-utils
      local -r rhel_version
      rhel_version="$(rpm -E %rhel)"
      # Check if Trivy repo already exists
      if ! sudo yum-config-manager --list-repos | grep -q "trivy"; then
        sudo yum-config-manager --add-repo "https://aquasecurity.github.io/trivy-repo/rhel/releases/download/${rhel_version}/trivy.repo"
      fi
      sudo yum install -y trivy
      ;;
    "dnf")
      sudo dnf install -y dnf-plugins-core
      local -r fedora_version
      fedora_version="$(rpm -E %fedora)"
      # Check if Trivy repo already exists
      if ! sudo dnf config-manager --list-repos | grep -q "trivy"; then
        sudo dnf config-manager --add-repo "https://aquasecurity.github.io/trivy-repo/rhel/releases/download/${fedora_version}/trivy.repo"
      fi
      sudo dnf install -y trivy
      ;;
    "brew")
      brew install trivy
      ;;
    *)
      # Fallback to manual installation
      curl -sfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh | \
        sh -s -- -b /usr/local/bin
      ;;
  esac
}

# ARM64 toolchain installation (single responsibility)
install_arm64_toolchain_impl() {
  if [[ "$OSTYPE" != "linux-gnu"* ]]; then
    log_warn "Cross-compilation tools only supported on Linux"
    return 0
  fi

  local -r pkg_mgr="$(detect_package_manager)"
  if [[ "$pkg_mgr" != "apt" ]]; then
    log_warn "ARM64 toolchain only supported on Debian/Ubuntu"
    return 0
  fi

  # Detect available Python version
  local python_version
  python_version="$(python3 --version 2>&1 | grep -o '[0-9]\+\.[0-9]\+' | head -1)"
  log_info "Detected Python version: $python_version"

  # Install in batches for better error handling
  local -r gcc_packages=(gcc-aarch64-linux-gnu g++-aarch64-linux-gnu)
  local -r qemu_packages=(qemu-user-static)

  # Try to install ARM64 libc dev package (may not be available on all systems)
  local arm64_libc_package=""
  if apt-cache search "aarch64-linux-gnu-libc" | grep -q "aarch64-linux-gnu-libc.*dev"; then
    arm64_libc_package="aarch64-linux-gnu-libc6-dev"
  elif apt-cache search "libc6-dev-arm64" | grep -q "libc6-dev-arm64-cross"; then
    arm64_libc_package="libc6-dev-arm64-cross"
  fi

  install_packages_batch "${gcc_packages[@]}"
  install_packages_batch "${qemu_packages[@]}"

  # Install ARM64 libc dev if available
  if [[ -n "$arm64_libc_package" ]]; then
    if install_packages_batch "$arm64_libc_package"; then
      log_info "Installed ARM64 libc development package: $arm64_libc_package"
    else
      log_warn "Could not install ARM64 libc development package"
    fi
  else
    log_warn "ARM64 libc development package not available on this system"
  fi

  # Verify installation with multiple checks
  local verification_passed=false

  # Check for GCC compiler
  if command_exists_with_timeout "aarch64-linux-gnu-gcc"; then
    log_info "ARM64 GCC compiler found: $(aarch64-linux-gnu-gcc --version | head -n1)"
    verification_passed=true
  elif [[ -f "/usr/bin/aarch64-linux-gnu-gcc" ]]; then
    log_info "ARM64 GCC compiler found at /usr/bin/aarch64-linux-gnu-gcc"
    verification_passed=true
  elif [[ -f "/usr/local/bin/aarch64-linux-gnu-gcc" ]]; then
    log_info "ARM64 GCC compiler found at /usr/local/bin/aarch64-linux-gnu-gcc"
    verification_passed=true
  fi

  # Check for G++ compiler
  if command_exists_with_timeout "aarch64-linux-gnu-g++"; then
    log_info "ARM64 G++ compiler found: $(aarch64-linux-gnu-g++ --version | head -n1)"
    verification_passed=true
  elif [[ -f "/usr/bin/aarch64-linux-gnu-g++" ]]; then
    log_info "ARM64 G++ compiler found at /usr/bin/aarch64-linux-gnu-g++"
    verification_passed=true
  fi

  # Check for QEMU
  if command_exists_with_timeout "qemu-aarch64-static"; then
    log_info "QEMU ARM64 emulator found: $(qemu-aarch64-static --version | head -n1)"
    verification_passed=true
  elif [[ -f "/usr/bin/qemu-aarch64-static" ]]; then
    log_info "QEMU ARM64 emulator found at /usr/bin/qemu-aarch64-static"
    verification_passed=true
  fi

  if [[ "$verification_passed" == "true" ]]; then
    log_info "ARM64 cross-compilation tools installed successfully"
  else
    log_warn "ARM64 toolchain verification failed, but packages were installed"
    log_info "You may need to add /usr/bin to your PATH or restart your shell"
    log_info "Installed packages: gcc-aarch64-linux-gnu, g++-aarch64-linux-gnu, qemu-user-static"
    return 0  # Don't fail the entire script for this optional component
  fi
}

# AWS CLI installation (single responsibility)
install_aws_cli_impl() {
  local -r pkg_mgr="$(detect_package_manager)"

  case "$pkg_mgr" in
    "apt")
      # Check if AWS CLI is already installed via package manager first
      if dpkg -l | grep -q "^ii.*awscli"; then
        log_info "AWS CLI already installed via package manager"
        return 0
      fi

      # Check if AWS CLI is already installed manually
      if [[ -d "/usr/local/aws-cli" ]] && command -v aws >/dev/null 2>&1; then
        log_info "AWS CLI already installed manually"
        return 0
      fi

      # Install via official installer
      local tmp_dir
      tmp_dir="$(mktemp -d)"
      trap "rm -rf '$tmp_dir'" EXIT

      curl --connect-timeout "$DOWNLOAD_TIMEOUT_SEC" --max-time "$DOWNLOAD_TIMEOUT_SEC" "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "${tmp_dir}/awscliv2.zip"
      unzip "${tmp_dir}/awscliv2.zip" -d "${tmp_dir}"
      sudo "${tmp_dir}/aws/install" --update
      ;;
    "yum"|"dnf")
      sudo yum install -y awscli || sudo dnf install -y awscli
      ;;
    "brew")
      brew install awscli
      ;;
    *)
      log_error "Unsupported package manager for AWS CLI: $pkg_mgr"
      return 1
      ;;
  esac
}

# =============================================================================
# PYTHON ENVIRONMENT (Single Responsibility)
# =============================================================================

# Setup Python virtual environment with validation
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

  # Generate and install requirements
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

  # Install package in development mode
  if [[ -f "setup.py" ]]; then
    log_info "Installing package in development mode..."
    pip install -e .
  fi
}

# =============================================================================
# ACT INSTALLATION (GitHub Actions Local Runner)
# =============================================================================

# Install act (GitHub Actions local runner) - single responsibility
install_act_impl() {
  local -r pkg_mgr="$(detect_package_manager)"

  # Create local bin directory if it doesn't exist
  mkdir -p "$HOME/.local/bin"

  case "$pkg_mgr" in
    "apt"|"yum"|"dnf"|"brew")
      # Install act using the official installer to local bin (no sudo required)
      log_info "Installing act to ~/.local/bin..."
      curl --connect-timeout "$DOWNLOAD_TIMEOUT_SEC" --max-time "$DOWNLOAD_TIMEOUT_SEC" \
        https://raw.githubusercontent.com/nektos/act/master/install.sh | bash -s -- -b "$HOME/.local/bin"

      # Add to PATH if not already there
      if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
        log_info "Adding ~/.local/bin to PATH..."
        echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME/.bashrc"
        export PATH="$HOME/.local/bin:$PATH"
      fi
      ;;
    *)
      log_error "Unsupported package manager for act: $pkg_mgr"
      return 1
      ;;
  esac
}

# Setup ACT environment configuration
setup_act_environment() {
  log_section "Setting up ACT environment"

    # Create .env.local file if it doesn't exist
  if [[ ! -f ".env.local" ]]; then
    log_info "Creating .env.local file for act..."
    if [[ -f "scripts/act-config.env" ]]; then
        cp scripts/act-config.env .env.local
      log_warn "⚠️  Please edit .env.local and add your actual values"
      log_warn "   Required: GITHUB_TOKEN, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY"
      else
        # Create basic .env.local if template doesn't exist
        cat > .env.local << EOF
# Local environment variables for act
# Add your actual values here

# GitHub token (for GitHub API access)
GITHUB_TOKEN=your_github_token_here

# AWS credentials (for deployment)
AWS_ACCESS_KEY_ID=your_aws_access_key_here
AWS_SECRET_ACCESS_KEY=your_aws_secret_key_here
AWS_REGION=us-east-1

# Application settings
PYTHON_VERSION=${PYTHON_VERSION}
NODE_VERSION=${NODE_VERSION}
APP_NAME=meal-expense-tracker

# Environment
ENV=dev
TF_ENV=dev
EOF
      log_warn "⚠️  Please edit .env.local and add your actual values"
      fi
    else
    log_info ".env.local already exists"
    fi

    # Test act installation
  if command_exists "act"; then
    log_info "Testing act installation..."
    if act --list >/dev/null 2>&1; then
      log_info "act is working correctly!"
      echo -e "\n${GREEN}act usage:${NC}"
      echo -e "  ${YELLOW}make act-ci${NC}        # Run CI workflow locally"
      echo -e "  ${YELLOW}make act-pipeline${NC}   # Run pipeline workflow locally"
      echo -e "  ${YELLOW}act -l${NC}              # List available workflows"
    else
      log_warn "Warning: act test failed, but installation appears successful"
    fi
  else
    log_info "act not installed - install with: $SCRIPT_NAME --mode tools"
    log_info "ACT environment file (.env.local) has been created for when you install act"
  fi
}

# =============================================================================
# MAIN INSTALLATION WORKFLOW (Dependency Inversion)
# =============================================================================

# Core system dependencies
install_core_dependencies() {
  log_section "Installing core system dependencies"

  # Detect available Python packages
  local python_version
  python_version="$(python3 --version 2>&1 | grep -o '[0-9]\+\.[0-9]\+' | head -1)"
  log_info "Detected Python version: $python_version"

  # Build package list based on available Python version
  local core_packages=(git curl wget unzip jq)

  # Add Python packages based on what's available
  if apt-cache show "python${python_version}-pip" >/dev/null 2>&1; then
    core_packages+=("python${python_version}-pip")
  else
    core_packages+=(python3-pip)
  fi

  if apt-cache show "python${python_version}-venv" >/dev/null 2>&1; then
    core_packages+=("python${python_version}-venv")
  else
    core_packages+=(python3-venv)
  fi

  install_packages_batch "${core_packages[@]}"

  # System-specific packages
  local -r pkg_mgr="$(detect_package_manager)"
  case "$pkg_mgr" in
    "apt")
      # Try to install Python dev package for detected version
      local python_dev_package=""
      if apt-cache show "python${python_version}-dev" >/dev/null 2>&1; then
        python_dev_package="python${python_version}-dev"
      elif apt-cache show "python3-dev" >/dev/null 2>&1; then
        python_dev_package="python3-dev"
      fi

      local dev_packages=(libsqlite3-dev sqlite3 shfmt)
      if [[ -n "$python_dev_package" ]]; then
        dev_packages+=("$python_dev_package")
      fi

      install_packages_batch "${dev_packages[@]}"
      ;;
    "yum"|"dnf")
      install_packages_batch python3-devel sqlite-devel gcc shfmt
      ;;
  esac
}

# Install all tools using the interface
install_all_tools() {
  log_section "Installing development tools"

  install_tool_if_missing "trivy" install_trivy_impl
  install_tool_if_missing "terraform" install_terraform_impl
  install_tool_if_missing "aws" install_aws_cli_impl
  install_tool_if_missing "act" install_act_impl
  install_arm64_toolchain_impl
}

# Setup Docker (if not already installed)
setup_docker() {
  log_section "Setting up Docker"

  if command_exists_with_timeout "docker"; then
    log_info "Docker is already installed"
    return 0
  fi

  local -r pkg_mgr="$(detect_package_manager)"
  case "$pkg_mgr" in
    "apt")
    sudo apt-get update
    sudo apt-get install -y docker.io docker-compose
      ;;
    "yum"|"dnf")
    sudo yum install -y docker docker-compose || sudo dnf install -y docker docker-compose
    sudo systemctl enable --now docker
      ;;
    "brew")
    brew install --cask docker
      ;;
    *)
      log_error "Unsupported package manager for Docker: $pkg_mgr"
      return 1
      ;;
  esac

  # Add user to docker group if needed
  if ! groups "$USER" | grep -q '\bdocker\b'; then
    sudo usermod -aG docker "$USER"
    log_warn "Added user to docker group. Please log out and back in."
  fi
}

# Initialize project files
initialize_project() {
  log_section "Initializing project files"

  cd "$PROJECT_ROOT"

# Update version from git tags
  if [[ -f "scripts/update-version.py" ]]; then
if ! python scripts/update-version.py; then
      log_error "Failed to update version from git tags"
      return 1
    fi
fi

# Create .env file if it doesn't exist
  if [[ ! -f ".env" ]]; then
    log_info "Creating .env file..."
    cat > .env << EOF
FLASK_APP=wsgi:app
FLASK_ENV=development
DATABASE_URL=postgresql://localhost:5432/meal_expenses
SECRET_KEY=your-secret-key-here
EOF
fi

# Initialize database
  if [[ -f "init_db.py" ]]; then
    log_info "Initializing database..."
python init_db.py
  fi
}

# Start the application (final step)
start_application() {
  log_section "Starting application"

  # Activate virtual environment
  if [[ -f "venv/bin/activate" ]]; then
    log_info "Activating virtual environment..."
    source venv/bin/activate
  fi

  # Start the application
  if [[ -f "Makefile" ]] && make help | grep -q "run"; then
    log_info "Starting application with make run..."
make run
  else
    log_warn "Makefile not found or 'run' target not available"
    log_info "You can start the application manually with:"
    log_info "  source venv/bin/activate"
    log_info "  python wsgi.py"
  fi
}

# =============================================================================
# MODE-SPECIFIC FUNCTIONS
# =============================================================================

# Auto mode: intelligently detect what's needed
run_auto_mode() {
  log_info "🤖 Auto mode: Detecting and installing missing components"

  cd "$PROJECT_ROOT"

  # Check what's missing
  local missing_tools=()
  local tools=("terraform" "trivy" "aws" "docker")

  for tool in "${tools[@]}"; do
    if ! command_exists "$tool"; then
      missing_tools+=("$tool")
    fi
  done

  if [[ ${#missing_tools[@]} -gt 0 ]]; then
    log_warn "Missing system tools: ${missing_tools[*]}"
    log_info "Installing missing system tools..."
    install_core_dependencies
    install_all_tools
    setup_docker
  else
    log_info "✅ All system tools are installed"
  fi

  # Always setup Python environment
  if [[ "$SKIP_PYTHON" != "true" ]]; then
    setup_python_environment
  fi

  # Always initialize project
  if [[ "$SKIP_INIT" != "true" ]]; then
    initialize_project
  fi

  # Setup ACT if requested or missing
  if [[ "$SKIP_ACT" != "true" ]]; then
    setup_act_environment
  fi

  # Start application if requested
  if [[ "$START_APP" == "true" ]]; then
    start_application
  fi
}

# Full mode: complete setup with all tools
run_full_mode() {
  log_info "🚀 Full mode: Complete setup with all tools (sudo required)"

  cd "$PROJECT_ROOT"

  # Install all dependencies
  install_core_dependencies
  install_all_tools
  setup_docker

  # Setup Python environment
  if [[ "$SKIP_PYTHON" != "true" ]]; then
    setup_python_environment
  fi

  # Initialize project
  if [[ "$SKIP_INIT" != "true" ]]; then
    initialize_project
  fi

  # Setup ACT environment
  if [[ "$SKIP_ACT" != "true" ]]; then
    setup_act_environment
  fi

  # Start application if requested
  if [[ "$START_APP" == "true" ]]; then
    start_application
  fi
}

# Minimal mode: user-space setup without sudo
run_minimal_mode() {
  log_info "🔧 Minimal mode: User-space setup without sudo operations"

  cd "$PROJECT_ROOT"

  # Check what's missing
  local missing_tools=()
  local tools=("terraform" "trivy" "aws" "docker")

  for tool in "${tools[@]}"; do
    if ! command_exists "$tool"; then
      missing_tools+=("$tool")
    fi
  done

  if [[ ${#missing_tools[@]} -gt 0 ]]; then
    log_warn "Missing system tools: ${missing_tools[*]}"
    log_info "Run with --mode full to install missing tools:"
    log_info "  sudo $SCRIPT_NAME --mode full"
  else
    log_info "✅ All system tools are installed"
  fi

  # Setup Python environment (no sudo required)
  if [[ "$SKIP_PYTHON" != "true" ]]; then
    setup_python_environment
  fi

  # Initialize project (no sudo required)
  if [[ "$SKIP_INIT" != "true" ]]; then
    initialize_project
  fi

  # Setup ACT environment (no sudo required)
  if [[ "$SKIP_ACT" != "true" ]]; then
    setup_act_environment
  fi

  # Start application if requested
  if [[ "$START_APP" == "true" ]]; then
    start_application
  fi
}

# Debug mode: analyze system without making changes
run_debug_mode() {
  log_info "🔍 Debug mode: Analyzing system without making changes"

  # System information
  log_section "System Information"
  log_info "OS Type: $OSTYPE"
  log_info "Package Manager: $(detect_package_manager)"
  log_info "Python Version: $(python3 --version 2>&1 || echo 'Not available')"
  log_info "Project Root: $PROJECT_ROOT"
  log_info "Current User: $(whoami)"
  log_info "Home Directory: $HOME"

  # Check existing installations
  log_section "Existing Tool Installations"
  local tools=("terraform" "trivy" "aws" "act" "docker" "aarch64-linux-gnu-gcc" "qemu-aarch64-static")

  for tool in "${tools[@]}"; do
    if command_exists "$tool"; then
      log_info "$tool: ✅ Installed"
      if [[ "$tool" == "terraform" || "$tool" == "aws" || "$tool" == "trivy" ]]; then
        log_info "  Version: $($tool --version 2>/dev/null | head -n1 || echo 'Version check failed')"
      fi
    else
      log_warn "$tool: ❌ Not found"
    fi
  done

  # Python environment
  log_section "Python Environment"
  if command_exists python3; then
    log_info "Python3: ✅ Available"
    log_info "Version: $(python3 --version 2>&1)"
    log_info "Location: $(which python3)"

    if [[ -d "$PROJECT_ROOT/venv" ]]; then
      log_info "Virtual Environment: ✅ Exists at $PROJECT_ROOT/venv"
    else
      log_warn "Virtual Environment: ❌ Not found"
    fi

    if [[ -f "$PROJECT_ROOT/requirements.txt" ]]; then
      log_info "Requirements: ✅ Found requirements.txt"
    else
      log_warn "Requirements: ❌ requirements.txt not found"
    fi
  else
    log_error "Python3: ❌ Not available"
  fi

  # Project files
  log_section "Project Files"
  local files=(".env" "init_db.py" "scripts/update-version.py" "Makefile" "docker-compose.yml")

  for file in "${files[@]}"; do
    if [[ -f "$PROJECT_ROOT/$file" ]]; then
      log_info "$file: ✅ Exists"
    else
      log_warn "$file: ❌ Not found"
    fi
  done

  # Check for .env.local
  if [[ -f "$PROJECT_ROOT/.env.local" ]]; then
    log_info ".env.local: ✅ Exists"
  else
    log_warn ".env.local: ❌ Not found (will be created)"
  fi

  log_section "Debug Complete"
  log_info "✅ System analysis complete"
  log_info "This debug mode performed no installations or modifications"
}

# Python mode: Python environment only
run_python_mode() {
  log_info "🐍 Python mode: Python environment setup only"

  cd "$PROJECT_ROOT"
  setup_python_environment

  if [[ "$START_APP" == "true" ]]; then
    start_application
  fi
}

# Tools mode: system tools installation only
run_tools_mode() {
  log_info "🔧 Tools mode: System tools installation only"

  install_core_dependencies
  install_all_tools
  setup_docker
}

# ACT mode: GitHub Actions environment only
run_act_mode() {
  log_info "⚡ ACT mode: GitHub Actions environment setup only"

  cd "$PROJECT_ROOT"

  # Install ACT if not present
  if ! command_exists "act"; then
    log_info "Installing ACT..."
    install_act_impl
  else
    log_info "ACT is already installed"
  fi

  # Setup ACT environment
  setup_act_environment
}

# Start mode: application startup only
run_start_mode() {
  log_info "▶️  Start mode: Application startup only"

  cd "$PROJECT_ROOT"
  start_application
}

# =============================================================================
# MAIN EXECUTION (Open/Closed Principle)
# =============================================================================

main() {
  # Parse command line arguments
  parse_arguments "$@"

  log_info "🚀 Setting up local development environment..."
  log_info "Mode: $SETUP_MODE"
  log_debug "Debug mode enabled"

  # Change to project root
  cd "$PROJECT_ROOT"

  # Execute based on mode
  case "$SETUP_MODE" in
    "auto")
      run_auto_mode
      ;;
    "full")
      run_full_mode
      ;;
    "minimal")
      run_minimal_mode
      ;;
    "debug")
      run_debug_mode
      ;;
    "python")
      run_python_mode
      ;;
    "tools")
      run_tools_mode
      ;;
    "act")
      run_act_mode
      ;;
    "start")
      run_start_mode
      ;;
    *)
      log_error "Unknown mode: $SETUP_MODE"
      exit 1
      ;;
  esac

  # Print completion message
  log_section "Setup Complete!"
  log_info "✅ Development environment setup is complete!"

  echo -e "\nTo activate the virtual environment, run:"
  echo -e "  source venv/bin/activate\n"

  echo -e "${GREEN}Available commands:${NC}"
  echo -e "  ${YELLOW}make ci-local${NC}        # Run CI workflow locally"
  echo -e "  ${YELLOW}make ci-quick${NC}        # Run quick CI checks"
  echo -e "  ${YELLOW}make pipeline-local${NC}  # Run pipeline workflow locally"
  echo -e "  ${YELLOW}make act-ci${NC}          # Run CI workflow with act"
  echo -e "  ${YELLOW}make act-pipeline${NC}    # Run pipeline workflow with act"
}

# Run main function
main "$@"
