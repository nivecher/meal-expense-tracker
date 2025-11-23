#!/bin/bash
# Redeploy Lambda function with Docker container
# This script builds, tags, and deploys the Lambda container image

set -e  # Exit on error
set -o pipefail  # Exit on pipe failures

ECR_REPO="562427544284.dkr.ecr.us-east-1.amazonaws.com/meal-expense-tracker-dev-lambda"
FUNCTION_NAME="meal-expense-tracker-dev"
REGION="us-east-1"

# Logging function
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1"
}

# Error handler
error_exit() {
    log "❌ ERROR: $1"
    exit 1
}

log "🚀 Starting Lambda redeployment..."
log "   Function: ${FUNCTION_NAME}"
log "   ECR Repo: ${ECR_REPO}"
log "   Region: ${REGION}"

# Step 1: Build Docker image
log "🔨 Building Docker image..."
BUILD_TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%S+00:00")
log "   Build timestamp: ${BUILD_TIMESTAMP}"
if ! docker build \
    --platform linux/arm64 \
    --no-cache \
    --provenance=false \
    --sbom=false \
    --build-arg BUILD_TIMESTAMP="${BUILD_TIMESTAMP}" \
    -t meal-expense-tracker-dev-lambda:latest \
    -f Dockerfile.lambda .; then
    error_exit "Docker build failed"
fi
log "✅ Docker image built successfully"

# Step 2: Tag image
log "🏷️  Tagging image..."
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
if ! docker tag meal-expense-tracker-dev-lambda:latest ${ECR_REPO}:latest; then
    error_exit "Failed to tag image as latest"
fi
if ! docker tag meal-expense-tracker-dev-lambda:latest ${ECR_REPO}:${TIMESTAMP}; then
    error_exit "Failed to tag image with timestamp"
fi
log "✅ Image tagged: latest and ${TIMESTAMP}"

# Step 3: Login to ECR
log "🔐 Logging into ECR..."
if ! aws ecr get-login-password --region ${REGION} | docker login --username AWS --password-stdin ${ECR_REPO}; then
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
