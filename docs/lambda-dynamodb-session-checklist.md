# Lambda DynamoDB Session Configuration Checklist

## ✅ Configuration Verification Complete

This document summarizes the verification and fixes applied to ensure DynamoDB sessions work correctly in AWS Lambda deployment.

## 🔧 Issues Found and Fixed

### 1. ✅ **Missing Session Environment Variables**

**Issue**: Lambda function was not receiving required session configuration environment variables.

**Fix Applied**: Added session environment variables to Lambda configuration:

```hcl
# Session configuration
SESSION_TYPE            = var.session_type
SESSION_TABLE_NAME      = var.session_table_name
AWS_REGION             = var.aws_region
```

**Files Modified**:

- `terraform/modules/lambda/main.tf` (lines 321-324)

### 2. ✅ **DynamoDB Table Schema Mismatch**

**Issue**: DynamoDB table schema didn't match Flask-Session requirements.

**Problems Fixed**:

- ❌ Had unnecessary `range_key = "expires"`
- ❌ Used `PROVISIONED` billing mode with fixed capacity
- ❌ Had complex GSI that Flask-Session doesn't need
- ❌ Wrong TTL attribute name (`expires` instead of `ttl`)

**Fix Applied**:

```hcl
resource "aws_dynamodb_table" "sessions" {
  name         = var.table_name
  billing_mode = "PAY_PER_REQUEST"  # Auto-scaling
  hash_key     = "id"               # Only primary key needed

  # Correct TTL configuration
  ttl {
    attribute_name = "ttl"          # Flask-Session uses 'ttl'
    enabled        = true
  }
}
```

**Files Modified**:

- `terraform/modules/dynamodb/main.tf` (complete refactor)

### 3. ✅ **IAM Permissions**

**Status**: Already correctly configured ✅

**Verified Permissions**:

```json
{
  "Effect": "Allow",
  "Action": [
    "dynamodb:GetItem",
    "dynamodb:PutItem",
    "dynamodb:UpdateItem",
    "dynamodb:DeleteItem",
    "dynamodb:Query",
    "dynamodb:Scan",
    "dynamodb:BatchGetItem",
    "dynamodb:BatchWriteItem",
    "dynamodb:ConditionCheckItem"
  ],
  "Resource": [
    "arn:aws:dynamodb:${region}:${account}:table/${app_name}-${environment}-sessions",
    "arn:aws:dynamodb:${region}:${account}:table/${app_name}-${environment}-sessions/index/*"
  ]
}
```

**Files Verified**:

- `terraform/modules/iam/main.tf` (lines 101-119)

### 4. ✅ **Lambda Cold Start Optimization**

**Enhancement**: Added session validation and connectivity checks during Lambda initialization.

**Features Added**:

- Session configuration validation on cold start
- DynamoDB connectivity testing
- Enhanced logging for debugging
- Graceful error handling

**Files Modified**:

- `lambda_handler.py` (added `_validate_session_config` function)

## 🚀 Lambda Deployment Configuration Summary

### Required Environment Variables

```bash
# Automatically set by Terraform
SESSION_TYPE=dynamodb
SESSION_TABLE_NAME=${app_name}-${environment}-sessions
AWS_REGION=${aws_region}
```

### DynamoDB Table Configuration

```
Table Name: ${app_name}-${environment}-sessions
Billing Mode: PAY_PER_REQUEST (auto-scaling)
Primary Key: id (String)
TTL Attribute: ttl (Number, Unix timestamp)
Encryption: Customer-managed KMS key
Point-in-time Recovery: Enabled
```

### Session Security Settings

```
SESSION_USE_SIGNER: true
SESSION_PERMANENT: true
SESSION_COOKIE_SECURE: true (production)
SESSION_COOKIE_HTTPONLY: true
SESSION_COOKIE_SAMESITE: "Lax"
PERMANENT_SESSION_LIFETIME: 3600 seconds (1 hour)
```

## 🧪 Testing the Configuration

### 1. Local Testing with LocalStack

```bash
# Start LocalStack with DynamoDB
docker run -d -p 4566:4566 localstack/localstack

# Set environment variables
export SESSION_TYPE=dynamodb
export SESSION_TABLE_NAME=test-sessions
export AWS_REGION=us-east-1
export SESSION_DYNAMODB_ENDPOINT=http://localhost:4566

# Create test table
aws --endpoint-url=http://localhost:4566 dynamodb create-table \
    --table-name test-sessions \
    --attribute-definitions AttributeName=id,AttributeType=S \
    --key-schema AttributeName=id,KeyType=HASH \
    --billing-mode PAY_PER_REQUEST \
    --region us-east-1

# Enable TTL
aws --endpoint-url=http://localhost:4566 dynamodb update-time-to-live \
    --table-name test-sessions \
    --time-to-live-specification Enabled=true,AttributeName=ttl \
    --region us-east-1
```

### 2. Lambda Function Testing

```bash
# Deploy with Terraform
cd terraform/environments/dev
terraform apply

# Test Lambda function
aws lambda invoke \
    --function-name meal-expense-tracker-dev \
    --payload '{"httpMethod": "GET", "path": "/health"}' \
    response.json

# Check logs for session validation
aws logs filter-log-events \
    --log-group-name /aws/lambda/meal-expense-tracker-dev \
    --filter-pattern "session"
```

## 📋 Deployment Checklist

**✅ Terraform automatically manages deployment order with proper dependencies.**

### Standard Terraform Deployment:

```bash
cd terraform/environments/{environment}
terraform apply
```

Terraform will automatically:

1. [ ] Create DynamoDB table first (module.dynamodb)
2. [ ] Deploy Lambda function with table dependency
3. [ ] Set correct environment variables
4. [ ] Apply proper IAM permissions

### Manual Verification (Optional):

- [ ] Verify `SESSION_TABLE_NAME` environment variable is set correctly
- [ ] Confirm `AWS_REGION` matches DynamoDB table region
- [ ] Check DynamoDB table exists: `aws dynamodb describe-table --table-name meal-expense-tracker-{env}-sessions`

### Post-deployment Verification:

- [ ] Test session persistence across Lambda invocations
- [ ] Verify TTL is working for session cleanup
- [ ] Check CloudWatch logs for session validation messages
- [ ] Monitor DynamoDB table metrics
- [ ] Confirm no "CreateTable" attempts in logs

## 🔍 Troubleshooting

### Common Issues

1. **CreateTable AccessDeniedException**

   ```
   AccessDeniedException: User is not authorized to perform: dynamodb:CreateTable
   ```

   **Solution**: Terraform dependencies should prevent this. If it occurs:

   ```bash
   # Check if table exists
   aws dynamodb describe-table --table-name meal-expense-tracker-{env}-sessions

   # If table missing, re-run terraform
   terraform apply
   ```

   **Root Cause**: Flask-Session tries to create table if it doesn't exist. Terraform dependencies ensure table exists first.

2. **Session data not persisting**

   - Check Lambda logs for session validation errors
   - Verify DynamoDB table exists and is accessible
   - Confirm IAM permissions are correctly attached

3. **DynamoDB connection errors**

   - Verify AWS_REGION environment variable
   - Check Lambda VPC configuration if using private subnets
   - Confirm security groups allow outbound HTTPS to DynamoDB

4. **Session validation failures**

   - Check CloudWatch logs for detailed error messages
   - Verify all required environment variables are set
   - Test DynamoDB connectivity from Lambda console

5. **Flask-Session localhost warnings**
   - Ensure `SESSION_DYNAMODB` resource is properly configured
   - Verify `mypy-boto3-dynamodb` package is installed
   - Check that AWS credentials are available to Lambda

### Debug Commands

```bash
# Check Lambda environment variables
aws lambda get-function-configuration \
    --function-name meal-expense-tracker-dev \
    --query 'Environment.Variables'

# Test DynamoDB table access
aws dynamodb describe-table --table-name meal-expense-tracker-dev-sessions

# View Lambda logs
aws logs tail /aws/lambda/meal-expense-tracker-dev --follow
```

## ✅ Final Status

**All critical issues have been resolved:**

✅ Session environment variables configured  
✅ DynamoDB table schema corrected  
✅ IAM permissions verified  
✅ Lambda cold start optimization added  
✅ Comprehensive testing documentation provided

**The configuration is now ready for Lambda deployment with DynamoDB sessions.**
