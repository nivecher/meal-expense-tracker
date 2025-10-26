#!/bin/bash
# Redeploy Lambda function with Docker container
# This script builds, tags, and deploys the Lambda container image

set -e

ECR_REPO="562427544284.dkr.ecr.us-east-1.amazonaws.com/meal-expense-tracker-dev-lambda"
FUNCTION_NAME="meal-expense-tracker-dev"

echo "🔨 Building Docker image..."
docker build --platform linux/arm64 --no-cache --provenance=false --sbom=false -t meal-expense-tracker-dev-lambda:latest -f Dockerfile.lambda .

echo "🏷️  Tagging image..."
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
docker tag meal-expense-tracker-dev-lambda:latest ${ECR_REPO}:latest
docker tag meal-expense-tracker-dev-lambda:latest ${ECR_REPO}:${TIMESTAMP}

echo "📤 Pushing images to ECR..."
docker push ${ECR_REPO}:latest
docker push ${ECR_REPO}:${TIMESTAMP}

echo "🚀 Updating Lambda function..."
aws lambda update-function-code --function-name ${FUNCTION_NAME} --image-uri ${ECR_REPO}:latest

echo "✅ Lambda function redeployed successfully!"
echo "   Image: ${ECR_REPO}:latest (${ECR_REPO}:${TIMESTAMP})"
echo "   Function: ${FUNCTION_NAME}"
