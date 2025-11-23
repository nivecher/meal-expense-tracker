#!/bin/bash
set -e

# ============================================
# Lambda Package Script - Architecture-Aware
# ============================================

# Configuration
PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
ARCHITECTURE=${ARCHITECTURE:-arm64}  # Default to ARM64
BASE_OUTPUT_DIR="${PWD}/dist"
TEMP_DIR=$(mktemp -d)

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Clean up function
cleanup() {
  echo -e "${YELLOW}[*] Cleaning up temporary files...${NC}"
  if [ -d "${TEMP_DIR}" ] && [[ "${TEMP_DIR}" == /tmp/* ]]; then
    rm -rf "${TEMP_DIR}"
    echo -e "${GREEN}[✓] Temporary files cleaned up${NC}"
  fi
}

trap cleanup EXIT

# Function to display usage
show_help() {
  echo "Usage: $0 [OPTION]..."
  echo "Lambda packaging script with architecture-aware builds"
  echo ""
  echo "Options:"
  echo "  -a, --app         Package only the application"
  echo "  -l, --layer       Package dependencies layer (architecture-aware)"
  echo "  -b, --both        Package both app and layer"
  echo "  -f, -        Package app only for current architecture (DEFAULT)"
  echo "  --docker          Package as Docker container for Lambda deployment"
  echo "  --arm64           Build for ARM64 only"
  echo "  --x86_64          Build for x86_64 only"
  echo "  -h, --help        Show this help message"
  echo ""
  echo "Examples:"
  echo "  $0                # Package app only for current arch"
  echo "  $0 -a             # Package app only"
  echo "  $0 -l             # Package layer only (architecture-aware)"
  echo "  $0 -b             # Package both app and layer"
  echo "  $0 --docker       # Package as Docker container for Lambda"
  echo "  $0 -f --arm64     # build for ARM64 only"
}

# app packaging (no Docker, no cross-compilation)
package_app() {
  echo -e "${GREEN}[*] packaging application for ${ARCHITECTURE}...${NC}"

  local app_temp_dir="${TEMP_DIR}/app"
  mkdir -p "${app_temp_dir}"

  # Create directory structure
  mkdir -p "${app_temp_dir}/app"
  mkdir -p "${app_temp_dir}/migrations/versions"
  mkdir -p "${app_temp_dir}/instance"

  # Define files to exclude (optimized list)
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
    "tests"
    "test-data"
    "docs"
    "terraform"
    "dist"
    "build"
    "playwright-report"
    "test-results"
  )

  # Build rsync exclude string
  local exclude_opts=()
  for pattern in "${exclude_patterns[@]}"; do
    exclude_opts+=(--exclude="$pattern")
  done

  # Copy application code with exclusions
  echo -e "${YELLOW}[*] Copying application files...${NC}"
  rsync -a "${exclude_opts[@]}" app/ "${app_temp_dir}/app/"

  # Copy root Python files
  echo -e "${YELLOW}[*] Copying root Python files...${NC}"
  for py_file in *.py; do
    if [ -f "$py_file" ]; then
      cp "$py_file" "${app_temp_dir}/"
    fi
  done

  # Copy essential configuration files only
  echo -e "${YELLOW}[*] Copying configuration files...${NC}"
  [ -f "requirements.txt" ] && cp requirements.txt "${app_temp_dir}/"
  [ -f "config.py" ] && cp config.py "${app_temp_dir}/"

  # Install dependencies to app package (for Lambda functions without layers)
  echo -e "${YELLOW}[*] Installing dependencies to app package...${NC}"
  if [ -f "requirements.txt" ]; then
    # Create site-packages directory in app package
    mkdir -p "${app_temp_dir}/python/lib/python${PYTHON_VERSION}/site-packages"

    # Install dependencies to app package
    if [ "$use_local_venv" = true ]; then
      # Use local virtual environment for app packaging
      echo -e "${YELLOW}[*] Installing dependencies to app using local venv...${NC}"
      pip install -r requirements.txt --target "${app_temp_dir}/python/lib/python${PYTHON_VERSION}/site-packages" --no-cache-dir
    else
      # Use system Python directly
      echo -e "${YELLOW}[*] Installing dependencies to app using system Python...${NC}"
      python3 -m pip install -r requirements.txt --target "${app_temp_dir}/python/lib/python${PYTHON_VERSION}/site-packages" --no-cache-dir
    fi

    # Create version-agnostic symlink
    (cd "${app_temp_dir}/python/lib" && ln -sf "python${PYTHON_VERSION}" python3.13)
  fi

  # Copy migrations if they exist (lightweight)
  if [ -d "migrations" ]; then
    echo -e "${YELLOW}[*] Copying migrations...${NC}"
    rsync -a --exclude='__pycache__' --exclude='*.pyc' migrations/ "${app_temp_dir}/migrations/"
  fi

  # Create necessary __init__.py files
  echo -e "${YELLOW}[*] Ensuring package structure...${NC}"
  touch "${app_temp_dir}/__init__.py"
  [ ! -f "${app_temp_dir}/app/__init__.py" ] && touch "${app_temp_dir}/app/__init__.py"
  [ ! -f "${app_temp_dir}/app/auth/__init__.py" ] && touch "${app_temp_dir}/app/auth/__init__.py"
  [ ! -f "${app_temp_dir}/app/expenses/__init__.py" ] && touch "${app_temp_dir}/app/expenses/__init__.py"
  [ ! -f "${app_temp_dir}/app/restaurants/__init__.py" ] && touch "${app_temp_dir}/app/restaurants/__init__.py"

  # Set proper permissions
  find "${app_temp_dir}" -type f -name "*.py" -exec chmod 644 {} \;
  find "${app_temp_dir}" -type d -exec chmod 755 {} \;

  # Create output directory - architecture-first structure
  mkdir -p "${BASE_OUTPUT_DIR}/${ARCHITECTURE}/app"

  # Create ZIP file - architecture-first structure
  local app_zip="${BASE_OUTPUT_DIR}/${ARCHITECTURE}/app/app-${ARCHITECTURE}.zip"
  echo -e "${GREEN}[*] Creating deployment package: ${app_zip}...${NC}"

  # Remove any existing package
  rm -f "${app_zip}"

  # Create the zip file
  (cd "${app_temp_dir}" && zip -r9 "${app_zip}" .)

  # Verify the zip was created
  if [ ! -f "${app_zip}" ]; then
    echo -e "${RED}[!] Failed to create deployment package${NC}"
    exit 1
  fi

  echo -e "${GREEN}[✓] application package created: ${app_zip}${NC}"
  echo -e "${GREEN}[✓] Package size: $(du -h "${app_zip}" | cut -f1)${NC}"
}

# Parse command line arguments
PACKAGE_APP=true
PACKAGE_LAYER=false
PACKAGE_MODE=true
PACKAGE_DOCKER=false

while [[ $# -gt 0 ]]; do
  case $1 in
  -a | --app)
    PACKAGE_APP=true
    PACKAGE_MODE=true
    shift
    ;;
  -l | --layer)
    PACKAGE_APP=false
    PACKAGE_LAYER=true
    shift
    ;;
  -f | -)
    PACKAGE_APP=true
    PACKAGE_LAYER=false
    PACKAGE_MODE=true
    shift
    ;;
  -b | --both)
    PACKAGE_APP=true
    PACKAGE_LAYER=true
    shift
    ;;
  --docker)
    PACKAGE_DOCKER=true
    PACKAGE_APP=false
    PACKAGE_LAYER=false
    PACKAGE_MODE=false
    shift
    ;;
  --arm64)
    ARCHITECTURE="arm64"
    shift
    ;;
  --x86_64)
    ARCHITECTURE="x86_64"
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

echo -e "${GREEN}=== Lambda Package Script ===${NC}"
echo "Architecture: ${ARCHITECTURE}"
echo "Python Version: ${PYTHON_VERSION}"
echo "Mode: ${PACKAGE_MODE}"
echo "Docker Mode: ${PACKAGE_DOCKER}"

# layer packaging (architecture-aware)
package_layer() {
  echo -e "${GREEN}[*] packaging Lambda layer for ${ARCHITECTURE}...${NC}"

  local layer_temp_dir="${TEMP_DIR}/layer"
  local output_dir="${BASE_OUTPUT_DIR}/${ARCHITECTURE}/layers"
  local timestamp
  timestamp=$(date +%Y%m%d%H%M%S)
  local zip_name="python-dependencies-${ARCHITECTURE}-${timestamp}.zip"
  local latest_zip="${output_dir}/python-dependencies-${ARCHITECTURE}-latest.zip"

  # Check if target architecture matches current platform
  local current_arch
  current_arch=$(uname -m)

  # Try local virtual environment first for cross-architecture builds
  # Most Python packages are architecture-independent
  echo -e "${YELLOW}[*] Attempting local virtual environment build for ${ARCHITECTURE}...${NC}"

  # Try to use local Python environment first (works for most Python packages)
  local use_local_venv=false
  if [ -d "venv" ] || [ -d ".venv" ]; then
    echo -e "${YELLOW}[*] Found local virtual environment, testing...${NC}"

    # Test if the virtual environment works
    if [ -d "venv" ]; then
      source venv/bin/activate
    elif [ -d ".venv" ]; then
      source .venv/bin/activate
    fi

    # Test pip functionality with a more comprehensive check
    if pip --version >/dev/null 2>&1 && python3 -c "import pip._internal.operations.build" >/dev/null 2>&1; then
      echo -e "${YELLOW}[*] Using local virtual environment for layer packaging...${NC}"
      use_local_venv=true
    else
      echo -e "${YELLOW}[*] Local virtual environment has issues (pip internal modules missing), falling back to system Python...${NC}"
      deactivate 2>/dev/null || true
    fi
  fi

  if [ "$use_local_venv" = true ]; then
    # Use local virtual environment for layer packaging
    echo -e "${YELLOW}[*] Installing dependencies to layer using local venv...${NC}"
    pip install -r requirements.txt --target "${layer_temp_dir}/python/lib/python${PYTHON_VERSION}/site-packages" --no-cache-dir

    # Deactivate virtual environment
    deactivate 2>/dev/null || true

  else
    # Use system Python directly
    echo -e "${YELLOW}[*] Using system Python for layer packaging...${NC}"
    python3 -m pip install -r requirements.txt --target "${layer_temp_dir}/python/lib/python${PYTHON_VERSION}/site-packages" --no-cache-dir
  fi

  # Check if we have architecture-specific packages that require Docker
  if grep -qE "(psycopg2[^-]binary|psycopg2==|cryptography|numpy|pillow|scipy|lxml|pandas)" requirements.txt; then
    echo -e "${YELLOW}[*] Found architecture-specific packages that require Docker cross-compilation${NC}"
    echo -e "${YELLOW}[*] Using Docker to build layer for ${ARCHITECTURE}...${NC}"

    # Use Docker for architecture-specific packages
    if ! package_layer_docker; then
      echo -e "${YELLOW}[!] Docker layer packaging failed, falling back to local build${NC}"
      echo -e "${YELLOW}[!] Warning: Local build may not work correctly for ${ARCHITECTURE} architecture${NC}"
      echo -e "${YELLOW}[!] Consider using Docker for production deployments${NC}"
      # Continue with local build instead of failing
    else
      # Skip the local layer packaging since we used Docker successfully
      return 0
    fi
  fi

  # Create directories
  mkdir -p "${layer_temp_dir}/python/lib/python${PYTHON_VERSION}/site-packages"
  mkdir -p "${output_dir}"

  # Create version-agnostic symlink for better compatibility
  echo -e "${YELLOW}[*] Creating compatibility symlinks...${NC}"
  ln -sf "python${PYTHON_VERSION}" "${layer_temp_dir}/python/lib/python3.13"

  # Set proper permissions
  echo -e "${YELLOW}[*] Setting file permissions...${NC}"
  find "${layer_temp_dir}" -type f -name "*.py" -exec chmod 644 {} \;
  find "${layer_temp_dir}" -type d -exec chmod 755 {} \;

  # Create ZIP file
  echo -e "${GREEN}[*] Creating layer package: ${output_dir}/${zip_name}...${NC}"
  rm -f "${output_dir}/python-dependencies-${ARCHITECTURE}-"*.zip

  (cd "${layer_temp_dir}" && zip -r9 "${output_dir}/${zip_name}" .)

  # Update latest symlink
  ln -sf "${zip_name}" "${latest_zip}"

  echo -e "${GREEN}[✓] layer package created: ${output_dir}/${zip_name}${NC}"
  echo -e "${GREEN}[✓] Latest build: ${latest_zip}${NC}"
  echo -e "${GREEN}[✓] Package size: $(du -h "${output_dir}/${zip_name}" | cut -f1)${NC}"
}

# Docker-based layer packaging for cross-architecture builds
package_layer_docker() {
  echo -e "${GREEN}[*] Docker packaging Lambda layer for ${ARCHITECTURE}...${NC}"

  local layer_temp_dir="${TEMP_DIR}/layer_docker"
  local output_dir="${BASE_OUTPUT_DIR}/${ARCHITECTURE}/layers"
  local timestamp
  timestamp=$(date +%Y%m%d%H%M%S)
  local zip_name="python-dependencies-${ARCHITECTURE}-${timestamp}.zip"
  local latest_zip="${output_dir}/python-dependencies-${ARCHITECTURE}-latest.zip"

  # Create output directory
  mkdir -p "${output_dir}"
  chmod 755 "${output_dir}"

  # Check if Docker is available
  if ! command -v docker &>/dev/null; then
    echo -e "${RED}[!] Docker is not installed. Cannot build cross-architecture layer.${NC}"
    return 1
  fi

  # Create temporary Docker build directory
  local docker_build_dir="${TEMP_DIR}/docker_build_${timestamp}"
  mkdir -p "${docker_build_dir}"

  # Copy requirements.txt to the build context
  cp requirements.txt "${docker_build_dir}/"

  # Create a minimal Dockerfile for layer build
  cat >"${docker_build_dir}/Dockerfile" <<EOF
FROM python:${PYTHON_VERSION}-slim

# Install build dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    python3-dev \
    libffi-dev \
    libssl-dev \
    libpq-dev \
    zip \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

# Copy requirements
COPY requirements.txt .

# Create layer directory structure
RUN mkdir -p /output/python/lib/python${PYTHON_VERSION}/site-packages

# Install dependencies to layer directory
RUN pip install --no-cache-dir --upgrade pip && \
    pip install -r requirements.txt --target /output/python/lib/python${PYTHON_VERSION}/site-packages

# Create version-agnostic symlink
RUN ln -sf python${PYTHON_VERSION} /output/python/lib/python3.13

# Create the zip file
RUN cd /output && zip -r /tmp/layer.zip .

# Copy zip to volume mount point
CMD ["sh", "-c", "cp /tmp/layer.zip /output/layer.zip && chmod 644 /output/layer.zip"]
EOF

  # Build the Docker image
  local image_name="lambda-layer-builder:${ARCHITECTURE}-${PYTHON_VERSION}"

  echo -e "${YELLOW}[*] Building Docker image for ${ARCHITECTURE}...${NC}"
  # Use buildx for proper cross-platform builds
  if ! docker buildx build \
    --platform "linux/${ARCHITECTURE}" \
    --load \
    -t "${image_name}" \
    "${docker_build_dir}"; then
    echo -e "${RED}[!] Failed to build Docker image with buildx${NC}"
    echo -e "${YELLOW}[*] Trying regular docker build...${NC}"
    if ! docker build \
      --platform "linux/${ARCHITECTURE}" \
      -t "${image_name}" \
      "${docker_build_dir}"; then
      echo -e "${RED}[!] Failed to build Docker image${NC}"
      rm -rf "${docker_build_dir}"
      return 1
    fi
  fi

  # Create the output directory with correct permissions
  mkdir -p "${layer_temp_dir}"
  chmod 777 "${layer_temp_dir}"

  # Run the container to create the layer
  echo -e "${YELLOW}[*] Creating layer package...${NC}"
  if ! docker run --rm \
    -v "${layer_temp_dir}:/output" \
    -u "$(id -u):$(id -g)" \
    "${image_name}"; then
    echo -e "${RED}[!] Failed to build layer in Docker container${NC}"
    rm -rf "${docker_build_dir}" "${layer_temp_dir}"
    return 1
  fi

  # Fix permissions on the output files
  chmod 644 "${layer_temp_dir}/layer.zip" 2>/dev/null || true

  # Verify the zip file was created
  if [ ! -f "${layer_temp_dir}/layer.zip" ]; then
    echo -e "${RED}[!] Failed to find the built layer zip file${NC}"
    rm -rf "${docker_build_dir}" "${layer_temp_dir}"
    return 1
  fi

  # Remove any existing zip files for this architecture
  rm -f "${output_dir}/python-dependencies-${ARCHITECTURE}-"*.zip

  # Move the zip file to the output directory
  mv "${layer_temp_dir}/layer.zip" "${output_dir}/${zip_name}"

  # Update the latest symlink
  ln -sf "${zip_name}" "${latest_zip}"

  # Clean up
  rm -rf "${docker_build_dir}" "${layer_temp_dir}"

  echo -e "${GREEN}[✓] Docker layer package created: ${output_dir}/${zip_name}${NC}"
  echo -e "${GREEN}[✓] Latest build: ${latest_zip}${NC}"
  echo -e "${GREEN}[✓] Package size: $(du -h "${output_dir}/${zip_name}" | cut -f1)${NC}"
}

# Docker container packaging for Lambda deployment
package_docker() {
  echo -e "${GREEN}[*] Packaging Docker container for Lambda deployment...${NC}"

  # Check if Docker is available
  if ! command -v docker &>/dev/null; then
    echo -e "${RED}[!] Docker is not installed. Cannot build container.${NC}"
    exit 1
  fi

  # Check if Docker is running
  if ! docker info &>/dev/null; then
    echo -e "${RED}[!] Docker is not running. Please start Docker first.${NC}"
    exit 1
  fi

  # Set platform for cross-compilation
  local platform="linux/${ARCHITECTURE}"
  local image_name="meal-expense-tracker-lambda"
  local image_tag="${ARCHITECTURE}-$(date +%Y%m%d%H%M%S)"

  echo -e "${YELLOW}[*] Building Docker image for platform: ${platform}${NC}"
  echo -e "${YELLOW}[*] Image: ${image_name}:${image_tag}${NC}"

  # Build the Lambda container image
  if ! docker build \
    --target lambda \
    --platform "${platform}" \
    --tag "${image_name}:${image_tag}" \
    --tag "${image_name}:latest" \
    .; then
    echo -e "${RED}[!] Failed to build Lambda container image${NC}"
    exit 1
  fi

  echo -e "${GREEN}[✓] Lambda container image built successfully${NC}"
  echo -e "${GREEN}[✓] Image: ${image_name}:${image_tag}${NC}"

  # Show image size
  local image_size
  image_size=$(docker images --format "table {{.Size}}" "${image_name}:${image_tag}" | tail -n 1)
  echo -e "${GREEN}[✓] Image size: ${image_size}${NC}"

  # Show deployment instructions
  echo -e "\n${YELLOW}=== Docker Container Deployment Instructions ===${NC}"
  echo "To deploy to Lambda:"
  echo "1. Tag and push the image to your ECR repository:"
  echo "   aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <account>.dkr.ecr.us-east-1.amazonaws.com"
  echo "   docker tag ${image_name}:${image_tag} <account>.dkr.ecr.us-east-1.amazonaws.com/${image_name}:${image_tag}"
  echo "   docker push <account>.dkr.ecr.us-east-1.amazonaws.com/${image_name}:${image_tag}"
  echo ""
  echo "2. Create a Lambda function using the pushed image"
  echo "3. Set handler to: wsgi.lambda_handler"
  echo "4. Set architecture to: ${ARCHITECTURE}"
  echo "5. Configure environment variables (DATABASE_URL, GOOGLE_MAPS_API_KEY, etc.)"
  echo ""
  echo "For automated deployment, use: scripts/package-docker-lambda.sh --push"
}

if [ "$PACKAGE_DOCKER" = true ]; then
  package_docker
elif [ "$PACKAGE_APP" = true ]; then
  package_app
fi

if [ "$PACKAGE_LAYER" = true ]; then
  package_layer
fi

echo -e "${GREEN}[✓] packaging complete!${NC}"

# Show deployment instructions
if [ "$PACKAGE_DOCKER" = true ]; then
  echo -e "\n${YELLOW}Docker container packaging completed!${NC}"
  echo -e "Use the deployment instructions shown above to deploy to Lambda."
elif [ "$PACKAGE_APP" = true ]; then
  echo -e "\n${YELLOW}To deploy:${NC}"
  echo "1. Upload ${BASE_OUTPUT_DIR}/${ARCHITECTURE}/app/app-${ARCHITECTURE}.zip to your Lambda function"
  echo "2. Set handler to 'wsgi.lambda_handler'"
  echo "3. Set architecture to '${ARCHITECTURE}'"
fi
