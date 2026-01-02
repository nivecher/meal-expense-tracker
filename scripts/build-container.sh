#!/bin/bash
set -e

# ============================================
# AWS Lambda Container Image Build Script
# ============================================

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DOCKERFILE="${PROJECT_ROOT}/Dockerfile"
TARGET="lambda"
IMAGE_NAME="meal-expense-tracker"
# Get AWS region from CLI config or environment variable or use default
AWS_REGION="${AWS_REGION:-$(aws configure get region 2>/dev/null || echo "us-east-1")}"
AWS_ACCOUNT_ID="${AWS_ACCOUNT_ID:-}"
ECR_REPO_NAME="${ECR_REPO_NAME:-meal-expense-tracker-dev-lambda}"
TAG="${TAG:-latest}"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

# Function to display usage
show_help() {
  echo "Usage: $0 [OPTION]..."
  echo "Build and publish AWS Lambda container image"
  echo ""
  echo "Options:"
  echo "  -r, --region REGION       AWS region (default: from AWS CLI config, fallback: us-east-1)"
  echo "  -a, --account-id ID       AWS account ID"
  echo "  -n, --repo-name NAME      ECR repository name (default: meal-expense-tracker-dev-lambda)"
  echo "  -t, --tag TAG            Image tag (default: latest)"
  echo "  -p, --platform PLATFORM  Target platform (default: linux/arm64)"
  echo "  -h, --help               Show this help message"
  echo ""
  echo "Environment Variables:"
  echo "  AWS_REGION               AWS region (overrides CLI config)"
  echo "  AWS_ACCOUNT_ID           AWS account ID"
  echo "  ECR_REPO_NAME            ECR repository name"
  echo "  TAG                      Image tag"
  echo ""
  echo "Examples:"
  echo "  $0                        # Build for ARM64 using AWS CLI configured region"
  echo "  $0 -r us-east-1 -t v1.0.0 # Build for us-east-1 with v1.0.0 tag"
  echo "  $0 --platform linux/amd64 # Build for x86_64 architecture"
  echo "  AWS_REGION=us-east-1 $0   # Override region via environment variable"
}

# Function to validate requirements
validate_requirements() {
  echo -e "${BLUE}[*] Validating requirements...${NC}"

  # Check if Dockerfile exists
  if [ ! -f "$DOCKERFILE" ]; then
    echo -e "${RED}[!] Dockerfile not found: $DOCKERFILE${NC}"
    exit 1
  fi

  # Check if AWS CLI is available
  if ! command -v aws &>/dev/null; then
    echo -e "${RED}[!] AWS CLI is not installed${NC}"
    exit 1
  fi

  # Check if Docker is available
  if ! command -v docker &>/dev/null; then
    echo -e "${RED}[!] Docker is not installed${NC}"
    exit 1
  fi

  # Check if Docker Buildx is available
  if ! docker buildx version &>/dev/null; then
    echo -e "${YELLOW}[!] Docker Buildx not found, installing...${NC}"
    docker buildx install
  fi

  echo -e "${GREEN}[✓] All requirements validated${NC}"
}

# Function to get AWS account ID
get_account_id() {
  if [ -z "$AWS_ACCOUNT_ID" ]; then
    echo -e "${YELLOW}[*] Getting AWS account ID...${NC}"
    AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
    if [ -z "$AWS_ACCOUNT_ID" ]; then
      echo -e "${RED}[!] Could not get AWS account ID. Please set AWS_ACCOUNT_ID environment variable or configure AWS CLI.${NC}"
      exit 1
    fi
    echo -e "${GREEN}[✓] AWS Account ID: $AWS_ACCOUNT_ID${NC}"
  fi
}

# Function to login to ECR
login_to_ecr() {
  echo -e "${BLUE}[*] Logging into ECR...${NC}"
  aws ecr get-login-password --region "$AWS_REGION" | docker login --username AWS --password-stdin "${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
  echo -e "${GREEN}[✓] Logged into ECR${NC}"
}

# Function to create ECR repository if it doesn't exist
create_ecr_repo() {
  echo -e "${BLUE}[*] Checking ECR repository...${NC}"

  if ! aws ecr describe-repositories --repository-names "$ECR_REPO_NAME" --region "$AWS_REGION" &>/dev/null; then
    echo -e "${YELLOW}[*] Creating ECR repository: $ECR_REPO_NAME${NC}"
    aws ecr create-repository \
      --repository-name "$ECR_REPO_NAME" \
      --region "$AWS_REGION" \
      --image-scanning-configuration scanOnPush=true \
      --encryption-configuration encryptionType=KMS
    echo -e "${GREEN}[✓] ECR repository created${NC}"
  else
    echo -e "${GREEN}[✓] ECR repository already exists${NC}"
  fi
}

# Function to build container image
build_image() {
  local platform="${1:-linux/arm64}"
  local full_image_name="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPO_NAME}:${TAG}"

  echo -e "${BLUE}[*] Building container image for platform: $platform${NC}"
  echo -e "${BLUE}[*] Image: $full_image_name${NC}"

  # Build the image with Buildx for cross-platform support
  docker buildx build \
    --platform "$platform" \
    --target "$TARGET" \
    --tag "$IMAGE_NAME:${TAG}" \
    --tag "$full_image_name" \
    --file "$DOCKERFILE" \
    --load \
    "$PROJECT_ROOT"

  echo -e "${GREEN}[✓] Container image built successfully${NC}"
}

# Function to push image to ECR
push_image() {
  local full_image_name="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPO_NAME}:${TAG}"

  echo -e "${BLUE}[*] Pushing image to ECR...${NC}"

  # Push the image
  docker push "$full_image_name"

  echo -e "${GREEN}[✓] Image pushed to ECR${NC}"
  echo -e "${GREEN}[✓] Image URI: $full_image_name${NC}"
}

# Function to verify image in ECR
verify_image() {
  echo -e "${BLUE}[*] Verifying image in ECR...${NC}"

  local full_image_name="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPO_NAME}:${TAG}"

  if aws ecr describe-images --repository-name "$ECR_REPO_NAME" --image-ids imageTag="$TAG" --region "$AWS_REGION" &>/dev/null; then
    echo -e "${GREEN}[✓] Image verified in ECR${NC}"

    # Get image digest
    local digest=$(aws ecr describe-images --repository-name "$ECR_REPO_NAME" --image-ids imageTag="$TAG" --region "$AWS_REGION" --query 'imageDetails[0].imageDigest' --output text)
    echo -e "${BLUE}[*] Image Digest: sha256:$digest${NC}"
  else
    echo -e "${RED}[!] Image not found in ECR${NC}"
    exit 1
  fi
}

# Function to clean up local images
cleanup() {
  echo -e "${YELLOW}[*] Cleaning up local images...${NC}"

  # Remove local tags
  docker rmi "$IMAGE_NAME:${TAG}" 2>/dev/null || true
  docker rmi "${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPO_NAME}:${TAG}" 2>/dev/null || true

  echo -e "${GREEN}[✓] Cleanup completed${NC}"
}

# Main execution
main() {
  local platform="linux/arm64"

  # Parse command line arguments
  while [[ $# -gt 0 ]]; do
    case $1 in
      -r | --region)
        AWS_REGION="$2"
        shift 2
        ;;
      -a | --account-id)
        AWS_ACCOUNT_ID="$2"
        shift 2
        ;;
      -n | --repo-name)
        ECR_REPO_NAME="$2"
        shift 2
        ;;
      -t | --tag)
        TAG="$2"
        shift 2
        ;;
      -p | --platform)
        platform="$2"
        shift 2
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

  echo -e "${GREEN}=== AWS Lambda Container Image Build ===${NC}"
  echo "Platform: $platform"
  echo "Region: $AWS_REGION (from AWS CLI config)"
  echo "Repository: $ECR_REPO_NAME"
  echo "Tag: $TAG"
  echo ""

  # Validate requirements
  validate_requirements

  # Get AWS account ID if not provided
  get_account_id

  # Login to ECR
  login_to_ecr

  # Create ECR repository if needed
  create_ecr_repo

  # Build container image
  build_image "$platform"

  # Push image to ECR
  push_image

  # Verify image in ECR
  verify_image

  # Cleanup local images
  cleanup

  echo -e "${GREEN}[✓] Container image build and deployment completed!${NC}"
  echo ""
  echo -e "${YELLOW}Next steps:${NC}"
  echo "1. Update your Terraform configuration to use the container image"
  echo "2. Run 'terraform apply' to deploy the updated Lambda function"
  echo "3. The Lambda function will now use the container image instead of layers"
}

# Run the script
main "$@"
