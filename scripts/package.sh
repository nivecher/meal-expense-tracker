#!/bin/bash
set -e

# Configuration
: "${PYTHON_VERSION:=3.13}" # Default to 3.13 if not set in environment
OUTPUT_DIR="${PWD}/dist"
TEMP_DIR=$(mktemp -d)

# Paths
SECRET_ROTATION_DIR="${PWD}/terraform/lambda/secret_rotation"

echo "Using Python version: $PYTHON_VERSION"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Clean up function
cleanup() {
  echo -e "${YELLOW}[*] Cleaning up temporary files...${NC}"
  rm -rf "${TEMP_DIR}"
  echo -e "${GREEN}[✓] Cleanup complete${NC}"
}

# Set up trap to ensure cleanup happens even on error
trap cleanup EXIT

# Ensure clean output directory
echo -e "${YELLOW}[*] Cleaning output directory: ${OUTPUT_DIR}${NC}"
rm -rf "${OUTPUT_DIR}"
mkdir -p "${OUTPUT_DIR}"

# Function to display usage information
show_help() {
  echo "Usage: $0 [OPTION]..."
  echo "Package the Lambda application and/or its dependencies"
  echo ""
  echo "Options:"
  echo "  -a, --app          Package the application code (default)"
  echo "  -l, --layer        Package the dependencies as a Lambda layer"
  echo "  -b, --both         Package both the application and layer"
  echo "  -s, --secrets      Package the secret rotation lambda"
  echo "  -h, --help         Show this help message"
  echo ""
  echo "Examples:"
  echo "  $0 -a              # Package only the application"
  echo "  $0 -l              # Package only the dependencies layer"
  echo "  $0 -b              # Package both application and dependencies"
  echo "  $0 -s              # Package only the secret rotation lambda"
  echo "  $0 -b -s           # Package all components (app, layer, and secret rotation)"
}

# Function to package the application
package_app() {
  echo -e "${GREEN}[*] Packaging application...${NC}"

  # Create a temporary directory for packaging
  local app_temp_dir="${TEMP_DIR}/app"
  mkdir -p "${app_temp_dir}"

  # Create necessary directories in the temp directory
  mkdir -p "${app_temp_dir}/app"
  mkdir -p "${app_temp_dir}/migrations/versions" # Ensure versions directory exists
  mkdir -p "${app_temp_dir}/scripts"
  mkdir -p "${app_temp_dir}/instance"

  # Define files and directories to exclude
  local exclude_patterns=(
    "__pycache__"
    "*.py[cod]"
    "*.so"
    "*.egg-info"
    ".DS_Store"
    "*.sqlite"
    "*.log"
    "*.swp"
    "*~"
    "*.bak"
    "*.tmp"
    ".pytest_cache"
    ".mypy_cache"
    ".coverage"
    "htmlcov"
    ".env.local"
    ".venv"
    "venv"
    "env"
    ".git"
    ".github"
    ".vscode"
    ".idea"
  )

  # Build rsync exclude string
  local exclude_opts=()
  for pattern in "${exclude_patterns[@]}"; do
    exclude_opts+=(--exclude="$pattern")
  done

  # Copy application code with exclusions
  echo -e "${YELLOW}[*] Copying application files...${NC}"
  rsync -a "${exclude_opts[@]}" app/ "${app_temp_dir}/app/"

  # Copy root Python files with exclusions
  echo -e "${YELLOW}[*] Copying root Python files...${NC}"
  for py_file in *.py; do
    if [ -f "$py_file" ]; then
      cp "$py_file" "${app_temp_dir}/"
    fi
  done

  # Copy required configuration files
  echo -e "${YELLOW}[*] Copying configuration files...${NC}"
  [ -f "requirements.txt" ] && cp requirements.txt "${app_temp_dir}/"
  [ -f "config.py" ] && cp config.py "${app_temp_dir}/"
  [ -f ".env.example" ] && cp .env.example "${app_temp_dir}/.env.example"

  # Copy migrations if they exist
  if [ -d "migrations" ]; then
    echo -e "${YELLOW}[*] Copying migrations...${NC}"
    rsync -a --exclude='__pycache__' --exclude='*.pyc' migrations/ "${app_temp_dir}/migrations/"
  fi

  # Create necessary __init__.py files if they don't exist
  echo -e "${YELLOW}[*] Ensuring package structure...${NC}"
  touch "${app_temp_dir}/__init__.py"
  [ ! -f "${app_temp_dir}/app/__init__.py" ] && touch "${app_temp_dir}/app/__init__.py"
  [ ! -f "${app_temp_dir}/app/auth/__init__.py" ] && touch "${app_temp_dir}/app/auth/__init__.py"
  [ ! -f "${app_temp_dir}/app/expenses/__init__.py" ] && touch "${app_temp_dir}/app/expenses/__init__.py"
  [ ! -f "${app_temp_dir}/app/restaurants/__init__.py" ] && touch "${app_temp_dir}/app/restaurants/__init__.py"

  # Copy specific script files if they exist
  local required_scripts=("check_rds.py" "check_db.py")
  for script in "${required_scripts[@]}"; do
    if [ -f "scripts/${script}" ]; then
      echo -e "${YELLOW}[*] Copying script: ${script}${NC}"
      mkdir -p "${app_temp_dir}/scripts"
      cp "scripts/${script}" "${app_temp_dir}/scripts/"
    fi
  done

  # Set proper permissions
  echo -e "${YELLOW}[*] Setting file permissions...${NC}"
  find "${app_temp_dir}" -type f -name "*.py" -exec chmod 644 {} \;
  find "${app_temp_dir}" -type d -exec chmod 755 {} \;

  # Create the deployment package
  echo -e "${GREEN}[*] Creating deployment package...${NC}"
  (cd "${app_temp_dir}" && zip -r9 "${OUTPUT_DIR}/app.zip" .)

  # Verify the zip was created
  if [ ! -f "${OUTPUT_DIR}/app.zip" ]; then
    echo -e "${RED}[!] Failed to create deployment package${NC}"
    exit 1
  fi

  echo -e "${GREEN}[✓] Application packaged: ${OUTPUT_DIR}/app.zip${NC}"
}

# Function to package the dependencies layer
package_layer() {
  echo -e "${GREEN}[*] Creating Lambda layer with Python dependencies...${NC}"

  # Create the Python package directory structure
  local layer_dir="${TEMP_DIR}/layer"
  local package_dir="${layer_dir}/python/lib/python${PYTHON_VERSION}/site-packages"
  mkdir -p "${package_dir}"

  # Install dependencies into the package directory
  echo -e "${GREEN}[*] Installing dependencies...${NC}"

  # Ensure we have the latest pip and pip-tools
  pip install --upgrade pip
  pip install --upgrade pip-tools

  # Install all requirements from requirements.txt with platform-specific wheels
  echo -e "${GREEN}[*] Installing dependencies from requirements.txt...${NC}"

  # First install platform-agnostic packages
  pip install -r <(grep -v '^#' requirements.txt | grep -v 'psycopg2-binary') \
    --target "${package_dir}" \
    --no-cache-dir \
    --upgrade

  # Install psycopg2-binary with platform-specific wheel
  if grep -q "psycopg2-binary" requirements.txt; then
    echo -e "${GREEN}[*] Installing psycopg2-binary with platform-specific wheel...${NC}"
    pip install --platform manylinux2014_x86_64 \
      --implementation cp \
      --python-version "${PYTHON_VERSION}" \
      --only-binary=:all: \
      --target "${package_dir}" \
      --no-cache-dir \
      --upgrade \
      "psycopg2-binary==$(grep 'psycopg2-binary' requirements.txt | grep -oE '[0-9]+\.[0-9]+\.[0-9]+')"
  fi

  # Remove unnecessary files
  echo -e "${GREEN}[*] Cleaning up...${NC}"
  find "${package_dir}" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
  find "${package_dir}" -type d -name "*.dist-info" -exec rm -rf {} + 2>/dev/null || true
  find "${package_dir}" -type d -name "tests" -exec rm -rf {} + 2>/dev/null || true

  # Create the ZIP file
  echo -e "${GREEN}[*] Creating ZIP file...${NC}"
  mkdir -p "${OUTPUT_DIR}/layers"
  (cd "${layer_dir}" && zip -r "${OUTPUT_DIR}/layers/python-dependencies.zip" .)

  echo -e "${GREEN}[✓] Lambda layer created: ${OUTPUT_DIR}/layers/python-dependencies.zip${NC}"
}

# Function to package the secret rotation lambda
package_secret_rotation() {
  local temp_dir="${TEMP_DIR}/secret_rotation"
  echo -e "${YELLOW}[*] Packaging secret rotation lambda...${NC}"

  # Create directory structure
  mkdir -p "${temp_dir}"

  # Copy Lambda function code
  if [ -f "${SECRET_ROTATION_DIR}/secret_rotation.py" ]; then
    cp "${SECRET_ROTATION_DIR}/secret_rotation.py" "${temp_dir}/"
  else
    echo -e "${RED}[!] Error: Secret rotation lambda code not found at ${SECRET_ROTATION_DIR}/secret_rotation.py${NC}"
    exit 1
  fi

  # Install dependencies
  if [ -f "${SECRET_ROTATION_DIR}/requirements.txt" ]; then
    echo -e "${YELLOW}[*] Installing secret rotation dependencies...${NC}"
    pip install -r "${SECRET_ROTATION_DIR}/requirements.txt" -t "${temp_dir}" --no-cache-dir
  else
    echo -e "${YELLOW}[*] No requirements.txt found for secret rotation, skipping dependency installation${NC}"
  fi

  # Create ZIP package
  echo -e "${YELLOW}[*] Creating secret rotation package...${NC}"
  (cd "${temp_dir}" && zip -r9 "${OUTPUT_DIR}/secret_rotation.zip" .)

  echo -e "${GREEN}[✓] Secret rotation package created: ${OUTPUT_DIR}/secret_rotation.zip${NC}"
}

# Parse command line arguments
PACKAGE_APP=false
PACKAGE_LAYER=false
PACKAGE_SECRETS=false

# Default to packaging app if no arguments provided
if [ $# -eq 0 ]; then
  PACKAGE_APP=true
  PACKAGE_LAYER=true
  PACKAGE_SECRETS=true
fi

while [[ $# -gt 0 ]]; do
  case $1 in
  -a | --app)
    PACKAGE_APP=true
    shift
    ;;
  -l | --layer)
    PACKAGE_LAYER=true
    shift
    ;;
  -b | --both)
    PACKAGE_APP=true
    PACKAGE_LAYER=true
    shift
    ;;
  -s | --secrets)
    PACKAGE_SECRETS=true
    shift
    ;;
  -h | --help)
    show_help
    exit 0
    ;;
  *)
    echo "Unknown option: $1"
    show_help
    exit 1
    ;;
  esac
done

# Package the requested components
if [ "$PACKAGE_APP" = true ]; then
  package_app
fi

if [ "$PACKAGE_LAYER" = true ]; then
  package_layer
fi

if [ "$PACKAGE_SECRETS" = true ]; then
  package_secret_rotation
fi

# Clean up the temporary directory
rm -rf "${TEMP_DIR}"

echo -e "${GREEN}[✓] Packaging complete!${NC}"

# Show deployment instructions
if [ "$PACKAGE_LAYER" = true ]; then
  echo -e "\n${YELLOW}To deploy the Lambda layer to AWS:${NC}"
  echo "1. Go to AWS Lambda Console"
  echo "2. Navigate to 'Layers'"
  echo "3. Click 'Create layer'"
  echo "4. Upload the ZIP file: ${OUTPUT_DIR}/layers/python-dependencies.zip"
  echo "5. Select Python ${PYTHON_VERSION} as the compatible runtime"
fi

if [ "$PACKAGE_APP" = true ]; then
  echo -e "\n${YELLOW}To deploy the application:${NC}"
  echo "1. Upload ${OUTPUT_DIR}/app.zip to your Lambda function"
  echo "2. Set the handler to 'wsgi.lambda_handler'"
fi
