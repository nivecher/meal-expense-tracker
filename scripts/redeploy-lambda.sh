#!/bin/bash
# Redeploy Lambda function with Docker container
# This script builds, tags, and deploys the Lambda container image
#
# Usage: ./scripts/redeploy-lambda.sh [options]
#
# Options:
#   --force, --rebuild    Force a rebuild even if no changes detected
#   --no-cache, --clean   Build without using Docker cache (clean build)
#
# Environment variables:
#   LAMBDA_ARCH           Architecture to build (x86_64 or arm64, default: x86_64)
#   AWS_ACCOUNT_ID        AWS account ID (auto-detected if not set)
#
# Build Detection:
#   The script automatically detects if a rebuild is needed by checking if key files
#   (Dockerfile, requirements.txt, app code) have changed since the last build.
#   Use --force to always rebuild.

set -e  # Exit on error
set -o pipefail  # Exit on pipe failures

# Get AWS account ID if not set (introspect from logged-in account)
if [ -z "${AWS_ACCOUNT_ID}" ]; then
    AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
    if [ -z "${AWS_ACCOUNT_ID}" ]; then
        echo "❌ ERROR: Could not determine AWS account ID. Please ensure AWS CLI is configured."
        exit 1
    fi
fi

ECR_REPO="${AWS_ACCOUNT_ID}.dkr.ecr.us-east-1.amazonaws.com/meal-expense-tracker-dev-lambda"
FUNCTION_NAME="meal-expense-tracker-dev"
REGION="us-east-1"

# Architecture configuration (can be overridden via LAMBDA_ARCH environment variable)
# Default to x86_64 for faster local builds (native architecture)
LAMBDA_ARCH="${LAMBDA_ARCH:-x86_64}"
PLATFORM="linux/${LAMBDA_ARCH}"
IMAGE_NAME="meal-expense-tracker-dev-lambda"

# Logging function
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1"
}

# Error handler
error_exit() {
    log "❌ ERROR: $1"
    exit 1
}

# Check if Docker daemon is running
check_docker() {
    if ! docker info >/dev/null 2>&1; then
        log "❌ ERROR: Docker daemon is not running"
        log ""
        log "To start Docker:"
        log "  • If using Docker Desktop: Start Docker Desktop application"
        log "  • If using Docker Engine: sudo systemctl start docker"
        log "  • If using Docker in WSL2: Ensure Docker Desktop is running on Windows"
        log ""
        exit 1
    fi
}

log "🚀 Starting Lambda redeployment..."
check_docker
log "   AWS Account ID: ${AWS_ACCOUNT_ID}"
log "   Function: ${FUNCTION_NAME}"
log "   ECR Repo: ${ECR_REPO}"
log "   Region: ${REGION}"
log "   Architecture: ${LAMBDA_ARCH}"

# Check if build is needed
NEED_BUILD=true
FORCE_BUILD=false

# Check for --force or --rebuild flag
if [[ "$*" == *"--force"* ]] || [[ "$*" == *"--rebuild"* ]]; then
    FORCE_BUILD=true
    log "   Build: FORCED (--force/--rebuild flag)"
elif docker image inspect ${IMAGE_NAME}:latest >/dev/null 2>&1; then
    # Image exists locally, check if we need to rebuild
    # Get image creation time as Unix timestamp
    IMAGE_TIME=$(docker image inspect ${IMAGE_NAME}:latest --format '{{.Created}}' 2>/dev/null || echo "")
    if [ -n "${IMAGE_TIME}" ]; then
        # Convert ISO timestamp to Unix timestamp (works on Linux)
        IMAGE_TIMESTAMP=$(date -d "${IMAGE_TIME}" +%s 2>/dev/null || date -jf "%Y-%m-%dT%H:%M:%S" "${IMAGE_TIME}" +%s 2>/dev/null || echo "0")
    else
        IMAGE_TIMESTAMP="0"
    fi

    # Check if key files are newer than the image
    NEED_REBUILD=false

    # Helper function to get file timestamp
    get_file_timestamp() {
        local file="$1"
        if [ -f "${file}" ]; then
            stat -c %Y "${file}" 2>/dev/null || stat -f %m "${file}" 2>/dev/null || echo "0"
        else
            echo "0"
        fi
    }

    # Check Dockerfile
    if [ "$(get_file_timestamp Dockerfile)" -gt "${IMAGE_TIMESTAMP}" ]; then
        NEED_REBUILD=true
        log "   Change detected: Dockerfile"
    fi

    # Check requirements.txt
    if [ "$(get_file_timestamp requirements.txt)" -gt "${IMAGE_TIMESTAMP}" ]; then
        NEED_REBUILD=true
        log "   Change detected: requirements.txt"
    fi

    # Check key Python files
    for file in wsgi.py lambda_handler.py lambda_init.py config.py; do
        if [ "$(get_file_timestamp "${file}")" -gt "${IMAGE_TIMESTAMP}" ]; then
            NEED_REBUILD=true
            log "   Change detected: ${file}"
            break
        fi
    done

    # Check app directory - sample a few key files (simple check)
    # Note: This doesn't check every file, but covers most cases
    # Use --force if you need to rebuild after changing untracked files
    for file in app/__init__.py app/api/routes.py app/services/ocr_service.py; do
        if [ -f "${file}" ] && [ "$(get_file_timestamp "${file}")" -gt "${IMAGE_TIMESTAMP}" ]; then
            NEED_REBUILD=true
            log "   Change detected: ${file}"
            break
        fi
    done

    if [ "${NEED_REBUILD}" = "false" ]; then
        NEED_BUILD=false
        log "   Build: SKIPPED (no changes detected, image is up to date)"
        log "   Use --force or --rebuild to force a rebuild"
    fi
else
    log "   Build: NEEDED (image not found locally)"
fi

# Step 1: Build Docker image (if needed)
if [ "${NEED_BUILD}" = "true" ] || [ "${FORCE_BUILD}" = "true" ]; then
    log "🔨 Building Docker image..."
    BUILD_TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%S+00:00")
    log "   Build timestamp: ${BUILD_TIMESTAMP}"
    log "   Platform: ${PLATFORM}"
    log "   Target: lambda"

    # Generate version file before building (if generate_version_file.py exists)
    # This ensures BUILD_TIMESTAMP is baked into the version file at build time
    if [ -f "scripts/generate_version_file.py" ]; then
        log "   Generating version file with build timestamp..."
        if BUILD_TIMESTAMP="${BUILD_TIMESTAMP}" python3 scripts/generate_version_file.py >/dev/null 2>&1; then
            log "   ✅ Version file generated with timestamp: ${BUILD_TIMESTAMP}"
        else
            log "   ⚠️  Warning: Could not generate version file (may need setuptools-scm)"
        fi
    fi

    # Check for --no-cache flag
    NO_CACHE=""
    if [[ "$*" == *"--no-cache"* ]] || [[ "$*" == *"--clean"* ]]; then
        NO_CACHE="--no-cache"
        log "   Cache: DISABLED (clean build)"
    else
        log "   Cache: ENABLED (faster rebuilds)"
    fi

    # Always use buildx with --provenance=false and --sbom=false for Lambda compatibility
    # Lambda requires Docker v2 schema manifest, not OCI format with attestations
    USE_BUILDX=false
    if docker buildx version >/dev/null 2>&1; then
        log "   Docker buildx is available"
        # Try to use the default builder, or create one if needed
        if docker buildx inspect default >/dev/null 2>&1; then
            docker buildx use default >/dev/null 2>&1 || true
            USE_BUILDX=true
        elif docker buildx inspect >/dev/null 2>&1; then
            # Use the current builder
            USE_BUILDX=true
        fi
    fi

    if [ "${USE_BUILDX}" = "true" ]; then
        log "   Using Docker buildx with Lambda-compatible flags"
        # Note: --provenance=false and --sbom=false required for Lambda compatibility
        # Lambda requires Docker v2 schema manifest, not OCI format with attestations
        if ! docker buildx build \
            --platform ${PLATFORM} \
            ${NO_CACHE} \
            --provenance=false \
            --sbom=false \
            --build-arg BUILD_TIMESTAMP="${BUILD_TIMESTAMP}" \
            --target lambda \
            --load \
            -t ${IMAGE_NAME}:latest \
            -f Dockerfile .; then
            error_exit "Docker buildx build failed"
        fi
    else
        log "   Using regular Docker build (buildx not available)"
        if ! docker build \
            ${NO_CACHE} \
            --build-arg BUILD_TIMESTAMP="${BUILD_TIMESTAMP}" \
            --target lambda \
            -t ${IMAGE_NAME}:latest \
            -f Dockerfile .; then
            error_exit "Docker build failed"
        fi
    fi
    log "✅ Docker image built successfully"
fi

# Step 2: Tag image
log "🏷️  Tagging image..."
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
if ! docker tag ${IMAGE_NAME}:latest ${ECR_REPO}:latest; then
    error_exit "Failed to tag image as latest"
fi
if ! docker tag ${IMAGE_NAME}:latest ${ECR_REPO}:${TIMESTAMP}; then
    error_exit "Failed to tag image with timestamp"
fi
log "✅ Image tagged: latest and ${TIMESTAMP}"

# Step 3: Login to ECR
log "🔐 Logging into ECR..."
# Workaround for WSL2 credential helper issues: store password in variable first
# This avoids credential helper failures that occur in WSL2 environments
ECR_PASSWORD=$(aws ecr get-login-password --region ${REGION})
if [ -z "${ECR_PASSWORD}" ]; then
    error_exit "Failed to get ECR login password"
fi
# Login and suppress credential helper warnings/errors (common in WSL2)
# The login will succeed even if credential storage fails
LOGIN_OUTPUT=$(echo "${ECR_PASSWORD}" | docker login --username AWS --password-stdin ${ECR_REPO} 2>&1)
LOGIN_STATUS=$?
# Filter out credential helper errors but check for actual login success
if [ ${LOGIN_STATUS} -ne 0 ] || ! echo "${LOGIN_OUTPUT}" | grep -q "Login Succeeded"; then
    error_exit "ECR login failed"
fi
log "✅ ECR login successful"

# Step 4: Push images
log "📤 Pushing images to ECR..."
if ! docker push ${ECR_REPO}:latest; then
    error_exit "Failed to push latest tag"
fi
log "✅ Pushed: latest"

if ! docker push ${ECR_REPO}:${TIMESTAMP}; then
    error_exit "Failed to push timestamp tag"
fi
log "✅ Pushed: ${TIMESTAMP}"

# Step 5: Update Lambda function
log "🚀 Updating Lambda function..."
if ! aws lambda update-function-code \
    --function-name ${FUNCTION_NAME} \
    --image-uri ${ECR_REPO}:latest \
    --region ${REGION} \
    --output json > /tmp/lambda-update.json 2>&1; then
    error_exit "Lambda update failed. Check /tmp/lambda-update.json for details"
fi

# Wait for Lambda to be ready
log "⏳ Waiting for Lambda function to be ready..."
aws lambda wait function-updated \
    --function-name ${FUNCTION_NAME} \
    --region ${REGION} || log "⚠️  Warning: Lambda wait timed out, but update may have succeeded"

log "✅ Lambda function redeployed successfully!"
log "   Image: ${ECR_REPO}:latest"
log "   Timestamp: ${ECR_REPO}:${TIMESTAMP}"
log "   Function: ${FUNCTION_NAME}"
log "   Region: ${REGION}"

# Show function status
log "📊 Function status:"
aws lambda get-function --function-name ${FUNCTION_NAME} --region ${REGION} --query 'Configuration.[FunctionName,LastUpdateStatus,CodeSize]' --output table 2>/dev/null || true
