#!/bin/bash
set -e

# Configuration
: "${PYTHON_VERSION:=3.13}" # Default to 3.13 if not set in environment
: "${ARCHITECTURE:=arm64}"  # Default to ARM64 if not set
BASE_OUTPUT_DIR="${PWD}/dist"
TEMP_DIR=$(mktemp -d)

# Paths
SECRET_ROTATION_DIR="${PWD}/terraform/lambda/secret_rotation"

# Function to set output directory based on architecture
set_output_dir() {
  OUTPUT_DIR="${BASE_OUTPUT_DIR}/${ARCHITECTURE}"
  mkdir -p "${OUTPUT_DIR}"
  # Ensure the layers directory exists
  mkdir -p "${OUTPUT_DIR}/layers"
  # Set proper permissions
  chmod 755 "${OUTPUT_DIR}" "${OUTPUT_DIR}/layers"
}

# Initialize output directory
set_output_dir

echo "Using Python version: ${PYTHON_VERSION}"
echo "Building for architecture: ${ARCHITECTURE}"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Clean up function - only removes temporary files, preserves build outputs
cleanup() {
  echo -e "${YELLOW}[*] Cleaning up temporary files...${NC}"
  # Only remove the temporary directory if it exists and is actually a subdirectory of /tmp
  if [ -d "${TEMP_DIR}" ] && [[ "${TEMP_DIR}" == /tmp/* ]]; then
    rm -rf "${TEMP_DIR}"
    echo -e "${GREEN}[✓] Temporary files cleaned up${NC}"
  fi
}

# Set up trap to ensure cleanup happens even on error
trap cleanup EXIT

# Ensure clean output directory for the specific architecture
echo -e "${YELLOW}[*] Preparing output directory: ${OUTPUT_DIR}${NC}"
mkdir -p "${OUTPUT_DIR}/layers"

# Function to display usage information
show_help() {
  echo "Usage: $0 [OPTION]..."
  echo "Package the Lambda application and/or its dependencies"
  echo ""
  echo "Options:"
  echo "  -a, --app         Package the application code"
  echo "  -l, --layer       Package the dependencies as a Lambda layer"
  echo "  -s, --secrets     Package the secret rotation lambda"
  echo "  -b, --both        Package both the application and layer (default: all)"
  echo "      --arm64       Only build for ARM64 architecture"
  echo "      --x86_64      Only build for x86_64 architecture"
  echo "  -h, --help        Show this help message"
  echo ""
  echo "By default, all components (app, layer, and secrets) are built for both architectures."
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

  # Create ZIP file with architecture in the name
  local app_zip="${OUTPUT_DIR}/app-${ARCHITECTURE}.zip"
  echo -e "${GREEN}[*] Creating deployment package: ${app_zip}...${NC}"

  # Remove any existing package to ensure clean build
  rm -f "${app_zip}"

  # Create the zip file
  (cd "${app_temp_dir}" && zip -r9 "${app_zip}" .)

  # Verify the zip was created
  if [ ! -f "${app_zip}" ]; then
    echo -e "${RED}[!] Failed to create deployment package${NC}"
    exit 1
  fi

  echo -e "${GREEN}[✓] Application packaged: ${app_zip}${NC}"
}

# Function to package the dependencies layer using Docker for ARM64 builds
package_layer() {
  echo -e "${GREEN}[*] Creating Lambda layer with Python dependencies for ARM64...${NC}"

  # Create a unique build directory for this layer build
  local timestamp
  timestamp=$(date +%Y%m%d%H%M%S)
  local layer_dir="${TEMP_DIR}/layer_${timestamp}"
  local output_dir="${OUTPUT_DIR}/layers"
  local zip_name="python-dependencies-${ARCHITECTURE}-${timestamp}.zip"
  local latest_zip="${output_dir}/python-dependencies-${ARCHITECTURE}-latest.zip"

  # Create output directory with proper permissions
  mkdir -p "${output_dir}"
  chmod 755 "${output_dir}"

  # Check if Docker is available
  if ! command -v docker &>/dev/null; then
    echo -e "${RED}[!] Docker is not installed. Please install Docker to build ARM64 layers.${NC}"
    return 1
  fi

  echo -e "${YELLOW}[*] Building ARM64 compatible layer using Docker...${NC}"

  # Create a temporary directory for the build context
  local docker_build_dir="${TEMP_DIR}/docker_build_${timestamp}"
  mkdir -p "${docker_build_dir}"

  # Copy requirements.txt to the build context
  cp requirements.txt "${docker_build_dir}/"

  # Create a Dockerfile for the build
  cat >"${docker_build_dir}/Dockerfile" <<'EOL'
# Use the appropriate Python image based on build arguments
ARG PYTHON_VERSION=3.13
FROM python:${PYTHON_VERSION}-slim

# Install build dependencies and zip utility
RUN apt-get update && apt-get install -y \
    gcc \
    python3-dev \
    zip \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

# Copy requirements
COPY requirements.txt .

# Create the layer directory structure for the specific Python version
RUN mkdir -p /output/python/lib/python${PYTHON_VERSION}/site-packages

# Also create a version-agnostic directory for better compatibility
RUN mkdir -p /output/python/lib/python3.13/site-packages

# Install dependencies to both version-specific and version-agnostic directories
RUN pip install --upgrade pip && \
    pip install -r requirements.txt --target /output/python/lib/python${PYTHON_VERSION}/site-packages && \
    # Copy to version-agnostic directory
    cp -r /output/python/lib/python${PYTHON_VERSION}/site-packages/* /output/python/lib/python3.13/site-packages/

# Create the zip file in a known location
RUN cd /output && zip -r /tmp/layer.zip .

# Set the output file as a build artifact
VOLUME [ "/output" ]

# Copy the zip file to the output directory
CMD ["sh", "-c", "cp /tmp/layer.zip /output/layer.zip && chmod 644 /output/layer.zip"]
EOL

  # Build the Docker image with architecture tag and platform
  local image_name="lambda-layer-builder:${ARCHITECTURE}-${PYTHON_VERSION}"
  if ! docker build \
    --platform "linux/${ARCHITECTURE}" \
    --build-arg PYTHON_VERSION="${PYTHON_VERSION}" \
    -t "${image_name}" \
    "${docker_build_dir}"; then
    echo -e "${RED}[!] Failed to build Docker image${NC}"
    return 1
  fi

  # Create the output directory with correct permissions
  mkdir -p "${layer_dir}"
  chmod 777 "${layer_dir}" # Ensure Docker can write to this directory

  # Run the container to create the layer with current user's UID/GID
  if ! docker run --rm \
    -v "${layer_dir}:/output" \
    -u "$(id -u):$(id -g)" \
    --platform "linux/${ARCHITECTURE}" \
    "${image_name}"; then
    echo -e "${RED}[!] Failed to build layer in Docker container${NC}"
    return 1
  fi

  # Fix permissions on the output files
  chmod 644 "${layer_dir}/layer.zip" 2>/dev/null || true

  # The zip file should be in the layer directory
  if [ ! -f "${layer_dir}/layer.zip" ]; then
    echo -e "${RED}[!] Failed to find the built layer zip file${NC}"
    return 1
  fi

  # Remove any existing zip files for this architecture to ensure clean build
  rm -f "${output_dir}/python-dependencies-${ARCHITECTURE}-"*.zip

  # Move the zip file to the output directory
  mv "${layer_dir}/layer.zip" "${output_dir}/${zip_name}"

  # Update the latest symlink
  ln -sf "${zip_name}" "${latest_zip}"

  echo -e "${GREEN}[✓] Layer ZIP created: ${output_dir}/${zip_name}${NC}"
  echo -e "${GREEN}[✓] Latest build symlink: ${latest_zip}${NC}"

  # Clean up
  rm -rf "${docker_build_dir}"

  echo -e "${GREEN}[✓] Lambda layer created: ${output_dir}/${zip_name}${NC}"
}

# Function to package the secret rotation lambda
package_secret_rotation() {
  local temp_dir="${TEMP_DIR}/secret_rotation"
  echo -e "${YELLOW}[*] Packaging secret rotation lambda...${NC}"

  # Create a unique virtual environment for the layer build with architecture in the name
  local timestamp
  timestamp=$(date +%Y%m%d%H%S)
  local venv_dir
  venv_dir="${TEMP_DIR}/layer_venv_${ARCHITECTURE}_${timestamp}"

  # Clean up any existing virtual environment
  if [ -d "${venv_dir}" ]; then
    rm -rf "${venv_dir}"
  fi

  echo -e "${YELLOW}[*] Creating virtual environment in ${venv_dir}...${NC}"
  "python${PYTHON_VERSION}" -m venv "${venv_dir}"
  # shellcheck source=/dev/null
  source "${venv_dir}/bin/activate"

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

  # Deactivate and remove the virtual environment
  deactivate
  rm -rf "${venv_dir}"

  # Create ZIP package with architecture in the name
  local secret_rotation_zip="${OUTPUT_DIR}/secret_rotation-${ARCHITECTURE}.zip"
  echo -e "${YELLOW}[*] Creating secret rotation package: ${secret_rotation_zip}...${NC}"

  # Remove any existing package to ensure clean build
  rm -f "${secret_rotation_zip}"

  # Create the zip file
  (cd "${temp_dir}" && zip -r9 "${secret_rotation_zip}" .)

  echo -e "${GREEN}[✓] Secret rotation package created: ${secret_rotation_zip}${NC}"
}

# Parse command line arguments
PACKAGE_APP=false
PACKAGE_LAYER=false
PACKAGE_SECRETS=false
BUILD_ARM64=true
BUILD_X86_64=true

# Default to packaging everything (app, layer, secrets) for both architectures
PACKAGE_APP=true
PACKAGE_LAYER=true
PACKAGE_SECRETS=true

# If specific components are requested, unset the others
if [ $# -gt 0 ]; then
  # Check if any component flags are provided
  for arg in "$@"; do
    case $arg in
    -a | --app | -l | --layer | -s | --secrets | -b | --both)
      # Reset all to false if specific components are requested
      PACKAGE_APP=false
      PACKAGE_LAYER=false
      PACKAGE_SECRETS=false
      break
      ;;
    esac
  done
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
    # Don't set PACKAGE_SECRETS here as -b/--both is specifically for app+layer
    shift
    ;;
  -s | --secrets)
    PACKAGE_SECRETS=true
    shift
    ;;
  --arm64)
    BUILD_ARM64=true
    BUILD_X86_64=false
    shift
    ;;
  --x86_64)
    BUILD_ARM64=false
    BUILD_X86_64=true
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

# Package the requested components for each architecture
package_for_architecture() {
  local arch=$1
  echo -e "\n${GREEN}=== Packaging for ${arch} ===${NC}"

  # Update architecture and output directory
  ARCHITECTURE="${arch}"
  set_output_dir

  if [ "$PACKAGE_APP" = true ]; then
    package_app
  fi

  if [ "$PACKAGE_LAYER" = true ]; then
    package_layer
  fi

  if [ "$PACKAGE_SECRETS" = true ]; then
    package_secret_rotation
  fi
}

# Build for each requested architecture
if [ "$BUILD_ARM64" = true ]; then
  package_for_architecture "arm64"
fi

if [ "$BUILD_X86_64" = true ]; then
  package_for_architecture "x86_64"
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
  echo "4. Upload the ZIP file: ${OUTPUT_DIR}/layers/python-dependencies-${ARCHITECTURE}-latest.zip"
  echo "5. Select Python ${PYTHON_VERSION} as the compatible runtime"
  echo "6. Select '${ARCHITECTURE}' as the compatible architecture"
fi

if [ "$PACKAGE_APP" = true ]; then
  echo -e "\n${YELLOW}To deploy the application:${NC}"
  echo "1. Upload ${OUTPUT_DIR}/app-${ARCHITECTURE}.zip to your Lambda function"
  echo "2. Set the handler to 'wsgi.lambda_handler'"
  echo "3. Set the architecture to '${ARCHITECTURE}' in the Lambda function configuration"
fi
