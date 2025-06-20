#!/bin/bash
set -e

# Configuration
: "${PYTHON_VERSION:=3.13}" # Default to 3.13 if not set in environment
OUTPUT_DIR="${PWD}/dist"
TEMP_DIR=$(mktemp -d)

echo "Using Python version: $PYTHON_VERSION"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Ensure output directory exists
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
  echo "  -h, --help         Show this help message"
  echo ""
  echo "Examples:"
  echo "  $0 -a              # Package only the application"
  echo "  $0 -l              # Package only the dependencies layer"
  echo "  $0 -b              # Package both application and dependencies"
}

# Function to package the application
package_app() {
  echo -e "${GREEN}[*] Packaging application...${NC}"

  # Create a temporary directory for packaging
  local app_temp_dir="${TEMP_DIR}/app"
  mkdir -p "${app_temp_dir}"

  # Copy application code and required files
  cp -r app/ "${app_temp_dir}/app"
  cp wsgi.py "${app_temp_dir}/"
  cp requirements.txt "${app_temp_dir}/"

  # Copy configuration files
  cp config.py "${app_temp_dir}/"
  cp .env.example "${app_temp_dir}/.env" 2>/dev/null || echo "No .env.example file found, continuing..."

  # Copy database check script
  mkdir -p "${app_temp_dir}/scripts"
  cp scripts/check_rds.py "${app_temp_dir}/scripts/"

  # Ensure all Python files are readable
  find "${app_temp_dir}" -type f -name "*.py" -exec chmod 644 {} \;

  # Create __init__.py in the root if it doesn't exist
  touch "${app_temp_dir}/__init__.py"

  # Create the deployment package
  (cd "${app_temp_dir}" && zip -r9 "${OUTPUT_DIR}/app.zip" .)

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

# Parse command line arguments
PACKAGE_APP=false
PACKAGE_LAYER=false

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
  -h | --help)
    show_help
    exit 0
    ;;
  *)
    echo -e "${YELLOW}Unknown option: $1${NC}"
    show_help
    exit 1
    ;;
  esac
done

# Default to packaging both if no options are provided
if [ "$PACKAGE_APP" = false ] && [ "$PACKAGE_LAYER" = false ]; then
  PACKAGE_APP=true
  PACKAGE_LAYER=true
fi

# Execute packaging
if [ "$PACKAGE_APP" = true ]; then
  package_app
fi

if [ "$PACKAGE_LAYER" = true ]; then
  package_layer
fi

# Clean up
rm -rf "${TEMP_DIR}"

echo -e "${GREEN}[✓] Packaging completed successfully!${NC}"

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
