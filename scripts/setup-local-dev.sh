#!/bin/bash

# Exit on error
set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print section headers
section() {
  echo -e "\n${GREEN}=== $1 ===${NC}"
}

# Function to install system packages
install_packages() {
  local packages=("$@")
  if command -v apt-get >/dev/null 2>&1; then
    # Debian/Ubuntu
    sudo apt-get update
    sudo apt-get install -y "${packages[@]}" || true
  elif command -v yum >/dev/null 2>&1; then
    # RHEL/CentOS
    sudo yum install -y "${packages[@]}" || true
  elif command -v dnf >/dev/null 2>&1; then
    # Fedora
    sudo dnf install -y "${packages[@]}" || true
  elif command -v brew >/dev/null 2>&1; then
    # macOS
    brew install "${packages[@]}" || true
  else
    echo -e "${YELLOW}Warning: Could not determine package manager. Please install dependencies manually.${NC}"
    return 1
  fi
}

# Function to install Terraform
install_terraform() {
  section "Installing Terraform"

  # Check if Terraform is already installed
  if command -v terraform >/dev/null 2>&1; then
    echo -e "${YELLOW}Terraform is already installed.${NC}"
    terraform version
    return 0
  fi

  # Create temp directory
  local tmp_dir
  tmp_dir=$(mktemp -d)

  # Download and install Terraform
  if command -v apt-get >/dev/null 2>&1; then
    # For Debian/Ubuntu
    wget -O- https://apt.releases.hashicorp.com/gpg | sudo gpg --dearmor -o /usr/share/keyrings/hashicorp-archive-keyring.gpg
    echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/hashicorp.list
    sudo apt-get update
    sudo apt-get install -y terraform
  elif command -v yum >/dev/null 2>&1; then
    # For RHEL/CentOS
    sudo yum install -y yum-utils
    sudo yum-config-manager --add-repo https://rpm.releases.hashicorp.com/RHEL/hashicorp.repo
    sudo yum -y install terraform
  elif command -v dnf >/dev/null 2>&1; then
    # For Fedora
    sudo dnf install -y dnf-plugins-core
    sudo dnf config-manager --add-repo https://rpm.releases.hashicorp.com/fedora/hashicorp.repo
    sudo dnf -y install terraform
  elif command -v brew >/dev/null 2>&1; then
    # For macOS
    brew tap hashicorp/tap
    brew install hashicorp/tap/terraform
  else
    # Fallback to manual installation
    echo -e "${YELLOW}Unsupported system. Attempting manual installation...${NC}"
    local tf_ver="1.5.7" # You can update this to the latest version
    local os_arch
    os_arch=$(uname -s | tr '[:upper:]' '[:lower:]')_$(uname -m | sed 's/x86_64/amd64/')
    local tf_url="https://releases.hashicorp.com/terraform/${tf_ver}/terraform_${tf_ver}_${os_arch}.zip"

    wget -q "$tf_url" -O "${tmp_dir}/terraform.zip"
    unzip -o "${tmp_dir}/terraform.zip" -d "${tmp_dir}"
    sudo install -o root -g root -m 0755 "${tmp_dir}/terraform" /usr/local/bin/terraform
  fi

  # Clean up
  rm -rf "$tmp_dir"

  # Verify installation
  if command -v terraform >/dev/null 2>&1; then
    echo -e "${GREEN}Terraform installed successfully!${NC}"
    terraform version
  else
    echo -e "${YELLOW}Failed to install Terraform. Please install it manually.${NC}"
    return 1
  fi
}

# Function to install Python requirements
install_python_requirements() {
  section "Setting up Python virtual environment"

  # Create virtual environment if it doesn't exist
  if [ ! -d "venv" ]; then
    python3 -m venv venv
  fi

  # Activate virtual environment
  source venv/bin/activate

  # Upgrade pip and install pip-tools
  python3 -m pip install --upgrade pip
  pip install pip-tools

  # Install base requirements
  section "Installing base requirements"
  pip install -r requirements/base.in

  # Install pre-commit, toml, and development requirements
  pip install pre-commit toml

  # Install development requirements
  section "Installing development requirements"
  pip install -r requirements/dev.in

  # Install security requirements
  section "Installing security requirements"
  pip install -r requirements/security.in

  # Install pre-commit hooks
  section "Setting up pre-commit hooks"
  pre-commit install
}

echo -e "\n${GREEN}🚀 Setting up local development environment...${NC}"

# Store the current directory
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

# Install system dependencies
section "Installing system dependencies"
if command -v apt-get >/dev/null 2>&1; then
  # Debian/Ubuntu
  install_packages libsqlite3-dev sqlite3 python3-pip python3-venv git curl jq unzip shfmt
elif command -v yum >/dev/null 2>&1 || command -v dnf >/dev/null 2>&1; then
  # RHEL/CentOS/Fedora
  install_packages python3-devel sqlite-devel gcc git curl jq unzip shfmt
else
  echo -e "${YELLOW}Unsupported system. Please install dependencies manually.${NC}"
  exit 1
fi

# Install Python requirements
install_python_requirements

# Install Terraform
install_terraform

# Print completion message
section "Setup Complete!"
echo -e "\n${GREEN}✅ Development environment setup is complete!${NC}"
echo -e "\nTo activate the virtual environment, run:"
echo -e "  source venv/bin/activate\n"

# Install Docker and Docker Compose
echo "Installing Docker..."
sudo apt-get update
sudo apt-get install -y docker.io docker-compose
sudo usermod -aG docker "$USER"

# Update version from git tags
if ! python scripts/update-version.py; then
  echo "Error: Failed to update version from git tags"
  exit 1
fi

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
  echo "Creating .env file..."
  {
    echo "FLASK_APP=app.py"
    echo "FLASK_ENV=development"
    echo "DATABASE_URL=postgresql://localhost:5432/meal_expenses"
    echo "SECRET_KEY=your-secret-key-here"
  } >.env
fi

# Initialize database
echo "Initializing database..."
python init_db.py

# Run locally
make run

echo "Local development environment setup complete!"
exit 0
