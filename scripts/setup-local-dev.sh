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
    echo "Creating Python virtual environment..."
    python3 -m venv venv
  else
    echo -e "${YELLOW}Virtual environment already exists.${NC}"
  fi

  # Activate virtual environment
  echo "Activating virtual environment..."
  # shellcheck source=/dev/null
  source venv/bin/activate

  # Upgrade pip
  echo "Upgrading pip..."
  pip install --upgrade pip

  # Install requirements
  echo "Installing Python requirements..."
  if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
  else
    echo -e "${YELLOW}requirements.txt not found. Skipping Python package installation.${NC}\n"
    echo -e "To install requirements later, run:"
    echo -e "  source venv/bin/activate"
    echo -e "  pip install -r requirements.txt"
    return 1
  fi

  # Install development requirements if they exist
  if [ -f "requirements-dev.txt" ]; then
    echo "Installing development requirements..."
    pip install -r requirements-dev.txt
  fi

  # Install package in development mode
  if [ -f "setup.py" ]; then
    echo "Installing package in development mode..."
    pip install -e .
  fi
}

# Function to install Trivy
install_trivy() {
  section "Installing Trivy"

  # Check if Trivy is already installed
  if command -v trivy >/dev/null 2>&1; then
    echo -e "${YELLOW}Trivy is already installed.${NC}"
    trivy --version
    return 0
  fi

  # Install Trivy based on the OS
  if command -v apt-get >/dev/null 2>&1; then
    # Debian/Ubuntu
    sudo apt-get install -y wget apt-transport-https gnupg lsb-release
    wget -qO - https://aquasecurity.github.io/trivy-repo/deb/public.key | gpg --dearmor | sudo tee /usr/share/keyrings/trivy.gpg >/dev/null
    echo "deb [signed-by=/usr/share/keyrings/trivy.gpg] https://aquasecurity.github.io/trivy-repo/deb $(lsb_release -sc) main" | sudo tee -a /etc/apt/sources.list.d/trivy.list
    sudo apt-get update
    sudo apt-get install -y trivy
  elif command -v yum >/dev/null 2>&1; then
    # RHEL/CentOS
    sudo yum install -y yum-utils
    rhel_version="$(rpm -E %rhel)"
    sudo yum-config-manager --add-repo "https://aquasecurity.github.io/trivy-repo/rhel/releases/download/${rhel_version}/trivy.repo"
    sudo yum install -y trivy
  elif command -v dnf >/dev/null 2>&1; then
    # Fedora
    sudo dnf install -y dnf-plugins-core
    fedora_version="$(rpm -E %fedora)"
    sudo dnf config-manager --add-repo "https://aquasecurity.github.io/trivy-repo/rhel/releases/download/${fedora_version}/trivy.repo"
    sudo dnf install -y trivy
  elif command -v brew >/dev/null 2>&1; then
    # macOS
    brew install trivy
  else
    # Fallback to manual installation
    echo -e "${YELLOW}Unsupported system. Attempting manual installation...${NC}"
    curl -sfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh | sh -s -- -b /usr/local/bin
  fi

  # Verify installation
  if command -v trivy >/dev/null 2>&1; then
    echo -e "${GREEN}Trivy installed successfully!${NC}"
    trivy --version
  else
    echo -e "${YELLOW}Failed to install Trivy. Please install it manually.${NC}"
    return 1
  fi
}

# Function to install and configure AWS CLI
install_aws_cli() {
  section "Setting up AWS CLI"

  # Check if AWS CLI is already installed
  if command -v aws &>/dev/null; then
    echo -e "${YELLOW}AWS CLI is already installed.${NC}"
    aws --version
    return 0
  fi

  echo "Installing AWS CLI..."

  # Install AWS CLI based on the system
  if command -v apt-get >/dev/null 2>&1; then
    # Debian/Ubuntu
    echo "Detected Debian/Ubuntu system"
    curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
    unzip awscliv2.zip
    sudo ./aws/install
    rm -rf aws awscliv2.zip
  elif command -v yum >/dev/null 2>&1 || command -v dnf >/dev/null 2>&1; then
    # RHEL/CentOS/Fedora
    echo "Detected RHEL/CentOS/Fedora system"
    sudo yum install -y awscli || sudo dnf install -y awscli
  elif command -v brew >/dev/null 2>&1; then
    # macOS
    echo "Detected macOS system"
    brew install awscli
  else
    echo -e "${YELLOW}Unsupported system. Please install AWS CLI manually.${NC}"
    return 1
  fi

  # Verify installation
  if aws --version; then
    echo -e "${GREEN}AWS CLI installed successfully!${NC}"

    # Configure AWS if not already configured
    if [ ! -f "$HOME/.aws/credentials" ] && [ ! -f "$HOME/.aws/config" ]; then
      echo -e "\n${YELLOW}AWS CLI is not configured. Please configure it with your credentials:${NC}"
      echo -e "Run: aws configure"
      echo -e "You'll need your AWS Access Key ID and Secret Access Key.${NC}"
    else
      echo -e "${GREEN}AWS CLI is already configured.${NC}"
    fi
  else
    echo -e "${YELLOW}Failed to verify AWS CLI installation.${NC}"
    return 1
  fi
}

echo -e "\n${GREEN}🚀 Setting up local development environment...${NC}"

# Store the current directory
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

# Install core dependencies
section "Installing core dependencies"
install_packages "git" "curl" "wget" "unzip" "jq" "python3-pip" "python3-venv"

# Install Trivy
install_trivy

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

# Install AWS CLI
install_aws_cli

# Print completion message
section "Setup Complete!"
echo -e "\n${GREEN}✅ Development environment setup is complete!${NC}"
echo -e "\nTo activate the virtual environment, run:"
echo -e "  source venv/bin/activate\n"

# Install Docker and Docker Compose
section "Installing Docker"
if ! command -v docker &>/dev/null; then
  echo "Installing Docker..."
  if command -v apt-get >/dev/null 2>&1; then
    # Debian/Ubuntu
    sudo apt-get update
    sudo apt-get install -y docker.io docker-compose
  elif command -v yum >/dev/null 2>&1 || command -v dnf >/dev/null 2>&1; then
    # RHEL/CentOS/Fedora
    sudo yum install -y docker docker-compose || sudo dnf install -y docker docker-compose
    sudo systemctl enable --now docker
  elif command -v brew >/dev/null 2>&1; then
    # macOS
    brew install --cask docker
  else
    echo -e "${YELLOW}Unsupported system. Please install Docker manually.${NC}"
  fi

  # Add user to docker group if not already
  if ! groups "$USER" | grep -q '\bdocker\b'; then
    sudo usermod -aG docker "$USER"
    echo -e "${YELLOW}You've been added to the docker group. Please log out and log back in for the changes to take effect.${NC}"
  fi
else
  echo -e "${YELLOW}Docker is already installed.${NC}"
fi

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
