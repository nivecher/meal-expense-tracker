#!/bin/bash
set -e

# ============================================
# Docker Lambda Container Packaging Script
# ============================================

# Configuration
PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
ARCHITECTURE=${ARCHITECTURE:-arm64}  # Default to ARM64
BASE_OUTPUT_DIR="${PWD}/dist"
TEMP_DIR=$(mktemp -d)
IMAGE_NAME="meal-expense-tracker-lambda"
IMAGE_TAG="${ARCHITECTURE}-$(date +%Y%m%d%H%M%S)"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
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
  echo "Docker Lambda container packaging script"
  echo ""
  echo "Options:"
  echo "  --arm64           Build for ARM64 architecture (default)"
  echo "  --x86_64          Build for x86_64 architecture"
  echo "  --push            Push image to ECR after building"
  echo "  --tag TAG         Use custom tag instead of timestamp"
  echo "  --no-cache        Build without using Docker cache"
  echo "  --test            Test the built container locally"
  echo "  -h, --help        Show this help message"
  echo ""
  echo "Examples:"
  echo "  $0                           # Build ARM64 container"
  echo "  $0 --x86_64                  # Build x86_64 container"
  echo "  $0 --push --tag v1.0.0       # Build and push with custom tag"
  echo "  $0 --test                    # Build and test locally"
}

# Parse command line arguments
PUSH_IMAGE=false
TEST_CONTAINER=false
NO_CACHE=""
CUSTOM_TAG=""

while [[ $# -gt 0 ]]; do
  case $1 in
  --arm64)
    ARCHITECTURE="arm64"
    shift
    ;;
  --x86_64)
    ARCHITECTURE="x86_64"
    shift
    ;;
  --push)
    PUSH_IMAGE=true
    shift
    ;;
  --tag)
    CUSTOM_TAG="$2"
    shift 2
    ;;
  --no-cache)
    NO_CACHE="--no-cache"
    shift
    ;;
  --test)
    TEST_CONTAINER=true
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

# Set custom tag if provided
if [ -n "$CUSTOM_TAG" ]; then
  IMAGE_TAG="$CUSTOM_TAG"
fi

echo -e "${GREEN}=== Docker Lambda Container Packaging ===${NC}"
echo "Architecture: ${ARCHITECTURE}"
echo "Python Version: ${PYTHON_VERSION}"
echo "Image: ${IMAGE_NAME}:${IMAGE_TAG}"
echo "Push to ECR: ${PUSH_IMAGE}"
echo "Test locally: ${TEST_CONTAINER}"

# Check prerequisites
check_prerequisites() {
  echo -e "${BLUE}[*] Checking prerequisites...${NC}"

  # Check if Docker is installed
  if ! command -v docker &>/dev/null; then
    echo -e "${RED}[!] Docker is not installed. Please install Docker first.${NC}"
    exit 1
  fi

  # Check if Docker is running
  if ! docker info &>/dev/null; then
    echo -e "${RED}[!] Docker is not running. Please start Docker first.${NC}"
    exit 1
  fi

  # Check if we're in the project root
  if [ ! -f "Dockerfile" ] || [ ! -f "requirements.txt" ]; then
    echo -e "${RED}[!] Please run this script from the project root directory.${NC}"
    exit 1
  fi

  # Check if AWS CLI is installed (for ECR push)
  if [ "$PUSH_IMAGE" = true ] && ! command -v aws &>/dev/null; then
    echo -e "${RED}[!] AWS CLI is not installed. Cannot push to ECR.${NC}"
    exit 1
  fi

  echo -e "${GREEN}[✓] Prerequisites check passed${NC}"
}

# Build Docker image for Lambda
build_lambda_image() {
  echo -e "${BLUE}[*] Building Lambda container image...${NC}"

  # Set platform for cross-compilation
  local platform="linux/${ARCHITECTURE}"

  echo -e "${YELLOW}[*] Building for platform: ${platform}${NC}"

  # Build the Lambda image
  if ! docker build \
    --target lambda \
    --platform "${platform}" \
    --tag "${IMAGE_NAME}:${IMAGE_TAG}" \
    --tag "${IMAGE_NAME}:latest" \
    ${NO_CACHE} \
    .; then
    echo -e "${RED}[!] Failed to build Lambda container image${NC}"
    exit 1
  fi

  echo -e "${GREEN}[✓] Lambda container image built successfully${NC}"
  echo -e "${GREEN}[✓] Image: ${IMAGE_NAME}:${IMAGE_TAG}${NC}"

  # Show image size
  local image_size
  image_size=$(docker images --format "table {{.Size}}" "${IMAGE_NAME}:${IMAGE_TAG}" | tail -n 1)
  echo -e "${GREEN}[✓] Image size: ${image_size}${NC}"
}

# Test the container locally
test_container() {
  echo -e "${BLUE}[*] Testing Lambda container locally...${NC}"

  # Create a test event
  local test_event='{
    "httpMethod": "GET",
    "path": "/health",
    "headers": {
      "Content-Type": "application/json"
    },
    "body": null,
    "isBase64Encoded": false,
    "requestContext": {
      "requestId": "test-request-id",
      "stage": "test",
      "resourcePath": "/health",
      "httpMethod": "GET",
      "requestTime": "2024-01-01T00:00:00.000Z",
      "protocol": "HTTP/1.1",
      "resourceId": "test-resource",
      "accountId": "123456789012",
      "apiId": "test-api",
      "identity": {}
    }
  }'

  # Run the container with test event
  echo -e "${YELLOW}[*] Running test event...${NC}"
  local container_id
  container_id=$(docker run -d \
    --platform "linux/${ARCHITECTURE}" \
    -e FLASK_ENV=production \
    -e DATABASE_URL="sqlite:///tmp/test.db" \
    "${IMAGE_NAME}:${IMAGE_TAG}")

  # Wait a moment for container to start
  sleep 2

  # Test the health endpoint
  echo -e "${YELLOW}[*] Testing health endpoint...${NC}"
  if docker exec "${container_id}" python3 -c "
import json
import sys
from lambda_handler import lambda_handler

# Test event
event = {
    'path': '/health',
    'httpMethod': 'GET',
    'headers': {'Content-Type': 'application/json'},
    'body': None,
    'isBase64Encoded': False,
    'requestContext': {
        'requestId': 'test-request-id',
        'stage': 'test',
        'resourcePath': '/health',
        'httpMethod': 'GET',
        'requestTime': '2024-01-01T00:00:00.000Z',
        'protocol': 'HTTP/1.1',
        'resourceId': 'test-resource',
        'accountId': '123456789012',
        'apiId': 'test-api',
        'identity': {}
    }
}

try:
    result = lambda_handler(event, {})
    print('Test result:', json.dumps(result, indent=2))
    if result.get('statusCode') == 200:
        print('SUCCESS: Health check passed')
        sys.exit(0)
    else:
        print('FAILED: Health check returned non-200 status')
        sys.exit(1)
except Exception as e:
    print('FAILED: Exception during test:', str(e))
    sys.exit(1)
"; then
    echo -e "${GREEN}[✓] Container test passed${NC}"
  else
    echo -e "${RED}[!] Container test failed${NC}"
    docker logs "${container_id}"
    docker stop "${container_id}" &>/dev/null || true
    exit 1
  fi

  # Clean up test container
  docker stop "${container_id}" &>/dev/null || true
  docker rm "${container_id}" &>/dev/null || true

  echo -e "${GREEN}[✓] Container testing completed successfully${NC}"
}

# Push image to ECR
push_to_ecr() {
  echo -e "${BLUE}[*] Pushing image to ECR...${NC}"

  # Get AWS account ID and region
  local aws_account_id
  aws_account_id=$(aws sts get-caller-identity --query Account --output text)
  local aws_region
  aws_region=$(aws configure get region || echo "us-east-1")

  local ecr_repo="${aws_account_id}.dkr.ecr.${aws_region}.amazonaws.com/${IMAGE_NAME}"

  echo -e "${YELLOW}[*] ECR repository: ${ecr_repo}${NC}"

  # Login to ECR
  echo -e "${YELLOW}[*] Logging in to ECR...${NC}"
  if ! aws ecr get-login-password --region "${aws_region}" | \
    docker login --username AWS --password-stdin "${ecr_repo}"; then
    echo -e "${RED}[!] Failed to login to ECR${NC}"
    exit 1
  fi

  # Tag image for ECR
  docker tag "${IMAGE_NAME}:${IMAGE_TAG}" "${ecr_repo}:${IMAGE_TAG}"
  docker tag "${IMAGE_NAME}:latest" "${ecr_repo}:latest"

  # Create repository if it doesn't exist
  echo -e "${YELLOW}[*] Ensuring ECR repository exists...${NC}"
  aws ecr describe-repositories --repository-names "${IMAGE_NAME}" --region "${aws_region}" &>/dev/null || \
    aws ecr create-repository --repository-name "${IMAGE_NAME}" --region "${aws_region}"

  # Push images
  echo -e "${YELLOW}[*] Pushing images to ECR...${NC}"
  if ! docker push "${ecr_repo}:${IMAGE_TAG}"; then
    echo -e "${RED}[!] Failed to push image with tag ${IMAGE_TAG}${NC}"
    exit 1
  fi

  if ! docker push "${ecr_repo}:latest"; then
    echo -e "${RED}[!] Failed to push latest image${NC}"
    exit 1
  fi

  echo -e "${GREEN}[✓] Images pushed to ECR successfully${NC}"
  echo -e "${GREEN}[✓] ECR URI: ${ecr_repo}:${IMAGE_TAG}${NC}"
}

# Generate deployment instructions
generate_deployment_instructions() {
  echo -e "\n${BLUE}=== Deployment Instructions ===${NC}"

  if [ "$PUSH_IMAGE" = true ]; then
    local aws_account_id
    aws_account_id=$(aws sts get-caller-identity --query Account --output text)
    local aws_region
    aws_region=$(aws configure get region || echo "us-east-1")
    local ecr_repo="${aws_account_id}.dkr.ecr.${aws_region}.amazonaws.com/${IMAGE_NAME}"

    echo -e "${GREEN}ECR Image URI: ${ecr_repo}:${IMAGE_TAG}${NC}"
    echo ""
    echo "To deploy to Lambda:"
    echo "1. Create a new Lambda function"
    echo "2. Choose 'Container image' as the package type"
    echo "3. Use this image URI: ${ecr_repo}:${IMAGE_TAG}"
    echo "4. Set the handler to: wsgi.lambda_handler"
    echo "5. Set the architecture to: ${ARCHITECTURE}"
    echo "6. Configure environment variables as needed"
    echo ""
    echo "Environment variables to set:"
    echo "- DATABASE_URL: Your PostgreSQL connection string"
    echo "- GOOGLE_MAPS_API_KEY: Your Google Maps API key"
    echo "- SECRET_KEY: A secure secret key for Flask"
    echo "- FLASK_ENV: production"
  else
    echo -e "${GREEN}Local Image: ${IMAGE_NAME}:${IMAGE_TAG}${NC}"
    echo ""
    echo "To deploy to Lambda:"
    echo "1. Tag and push the image to your ECR repository:"
    echo "   aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <account>.dkr.ecr.us-east-1.amazonaws.com"
    echo "   docker tag ${IMAGE_NAME}:${IMAGE_TAG} <account>.dkr.ecr.us-east-1.amazonaws.com/${IMAGE_NAME}:${IMAGE_TAG}"
    echo "   docker push <account>.dkr.ecr.us-east-1.amazonaws.com/${IMAGE_NAME}:${IMAGE_TAG}"
    echo ""
    echo "2. Create a Lambda function using the pushed image"
    echo "3. Set handler to: wsgi.lambda_handler"
    echo "4. Set architecture to: ${ARCHITECTURE}"
  fi

  echo ""
  echo "Lambda function configuration:"
  echo "- Memory: 512 MB (minimum recommended)"
  echo "- Timeout: 30 seconds (minimum recommended)"
  echo "- Architecture: ${ARCHITECTURE}"
  echo "- Handler: wsgi.lambda_handler"
}

# Main execution
main() {
  check_prerequisites
  build_lambda_image

  if [ "$TEST_CONTAINER" = true ]; then
    test_container
  fi

  if [ "$PUSH_IMAGE" = true ]; then
    push_to_ecr
  fi

  generate_deployment_instructions

  echo -e "\n${GREEN}[✓] Docker Lambda packaging completed successfully!${NC}"
}

# Run main function
main
