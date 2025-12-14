# Lambda Deployment Workflow

## Simplified Iterative Development

The Lambda function now uses the `latest` tag from ECR, eliminating the need to modify Terraform files during development iterations.

## Quick Deploy

Run the automated script:

```bash
./scripts/redeploy-lambda.sh
```

This script:

1. Builds the Docker image with ARM64 architecture
2. Tags it with both `latest` and a timestamp
3. Pushes both tags to ECR
4. Updates the Lambda function with the new image

## Manual Deploy

If you prefer manual control:

```bash
# 1. Get AWS account ID (auto-detected from logged-in account)
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# 2. Build the image
docker build --platform linux/arm64 --no-cache --provenance=false --sbom=false -t meal-expense-tracker-dev-lambda:latest -f Dockerfile.lambda .

# 3. Tag and push
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
docker tag meal-expense-tracker-dev-lambda:latest ${AWS_ACCOUNT_ID}.dkr.ecr.us-east-1.amazonaws.com/meal-expense-tracker-dev-lambda:latest
docker tag meal-expense-tracker-dev-lambda:latest ${AWS_ACCOUNT_ID}.dkr.ecr.us-east-1.amazonaws.com/meal-expense-tracker-dev-lambda:$TIMESTAMP

docker push ${AWS_ACCOUNT_ID}.dkr.ecr.us-east-1.amazonaws.com/meal-expense-tracker-dev-lambda:latest
docker push ${AWS_ACCOUNT_ID}.dkr.ecr.us-east-1.amazonaws.com/meal-expense-tracker-dev-lambda:$TIMESTAMP

# 4. Update Lambda
aws lambda update-function-code --function-name meal-expense-tracker-dev --image-uri ${AWS_ACCOUNT_ID}.dkr.ecr.us-east-1.amazonaws.com/meal-expense-tracker-dev-lambda:latest
```

## Benefits

- ✅ No Terraform file edits required during development
- ✅ Faster iteration cycle
- ✅ Automatic timestamp tags for tracking
- ✅ Latest tag always points to most recent build
- ✅ Easy rollback by using timestamp tags

## Terraform Changes

When making infrastructure changes (memory, timeout, environment variables, etc.), you'll still need to run `terraform apply`. This is only for code changes.

## First Time Setup

After running `terraform apply`, the Lambda function will automatically use the `latest` tag from ECR. All subsequent code changes can be deployed using the script above.
