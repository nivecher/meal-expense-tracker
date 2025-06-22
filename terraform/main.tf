# Main Terraform configuration
# This file serves as the entry point for Terraform

# Get the current AWS account ID
data "aws_caller_identity" "current" {}

# Get the current AWS region
data "aws_region" "current" {}

# Data sources for VPC endpoints
# We'll use specific endpoint IDs or names to avoid conflicts



# Generate a random password for Flask secret key
resource "random_password" "flask_secret_key" {
  length           = 50
  special          = true
  override_special = "!@#$%^&*()_+-=[]{}|;:,.<>?"
  min_lower        = 5
  min_numeric      = 5
  min_special      = 5
  min_upper        = 5
}

data "aws_vpc" "selected" {
  id = module.network.vpc_id
}

# Current region is set via the aws_region variable in variables.tf
locals {
  current_region = var.aws_region
  account_id     = data.aws_caller_identity.current.account_id


  # Set budget amount based on environment
  budget_amount = var.environment == "prod" ? "20.0" : "5.0"

  # Use provided monthly_budget_amount or default to environment-based amount
  monthly_budget = coalesce(var.monthly_budget_amount, local.budget_amount)
}

# S3 Bucket for Lambda deployment
resource "aws_s3_bucket" "lambda_deployment" {
  bucket = "${var.app_name}-${var.environment}-deployment-${data.aws_caller_identity.current.account_id}"

  tags = merge({
    Name        = "${var.app_name}-${var.environment}-deployment"
    Environment = var.environment
    ManagedBy   = "terraform"
  }, var.tags)
}

# Enable versioning on the S3 bucket
resource "aws_s3_bucket_versioning" "lambda_deployment" {
  bucket = aws_s3_bucket.lambda_deployment.id

  versioning_configuration {
    status = "Enabled"
  }
}

# Create a separate S3 bucket for access logs
resource "aws_s3_bucket" "access_logs" {
  bucket = "${var.app_name}-${var.environment}-access-logs-${data.aws_caller_identity.current.account_id}"

  tags = merge({
    Name        = "${var.app_name}-${var.environment}-access-logs"
    Environment = var.environment
    ManagedBy   = "terraform"
  }, var.tags)
}

# Enable server-side encryption for the access logs bucket
resource "aws_s3_bucket_server_side_encryption_configuration" "access_logs" {
  bucket = aws_s3_bucket.access_logs.id

  rule {
    apply_server_side_encryption_by_default {
      kms_master_key_id = aws_kms_key.main.arn
      sse_algorithm     = "aws:kms"
    }
  }
}

# Enable access logging for the access logs bucket (self-logging)
resource "aws_s3_bucket_logging" "access_logs" {
  bucket = aws_s3_bucket.access_logs.id

  target_bucket = aws_s3_bucket.access_logs.id
  target_prefix = "self-logs/"
}

# For the access logs bucket, we don't enable logging on itself as it would create a loop
# We'll use a lifecycle rule to manage the logs instead
resource "aws_s3_bucket_lifecycle_configuration" "access_logs" {
  bucket = aws_s3_bucket.access_logs.id

  rule {
    id     = "log"
    status = "Enabled"

    # Apply to all objects in the bucket
    filter {
      prefix = ""
    }

    expiration {
      days = 90 # Keep logs for 90 days
    }

    noncurrent_version_expiration {
      noncurrent_days = 30
    }
  }

  depends_on = [aws_s3_bucket_versioning.access_logs]
}

# Enable bucket owner preferred for access control
resource "aws_s3_bucket_ownership_controls" "access_logs" {
  bucket = aws_s3_bucket.access_logs.id

  rule {
    object_ownership = "BucketOwnerPreferred"
  }
}

# Enable versioning for the logs bucket
resource "aws_s3_bucket_versioning" "access_logs" {
  bucket = aws_s3_bucket.access_logs.id

  versioning_configuration {
    status = "Enabled"
  }

  depends_on = [aws_s3_bucket_ownership_controls.access_logs]
}



# Block public access to the logs bucket
resource "aws_s3_bucket_public_access_block" "access_logs" {
  bucket = aws_s3_bucket.access_logs.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# S3 bucket policy for lambda deployment bucket
resource "aws_s3_bucket_policy" "lambda_deployment" {
  bucket = aws_s3_bucket.lambda_deployment.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "AllowSSLRequestsOnly"
        Effect    = "Deny"
        Principal = "*"
        Action    = "s3:*"
        Resource = [
          aws_s3_bucket.lambda_deployment.arn,
          "${aws_s3_bucket.lambda_deployment.arn}/*"
        ]
        Condition = {
          Bool = {
            "aws:SecureTransport" = "false"
          }
        }
      },
      {
        Sid    = "AllowS3LogDelivery"
        Effect = "Allow"
        Principal = {
          Service = "logging.s3.amazonaws.com"
        }
        Action = [
          "s3:PutObject"
        ]
        Resource = "${aws_s3_bucket.lambda_deployment.arn}/s3/${var.app_name}-${var.environment}-deployment/*"
        Condition = {
          StringEquals = {
            "s3:x-amz-acl"      = "bucket-owner-full-control"
            "aws:SourceAccount" = data.aws_caller_identity.current.account_id
          }
          ArnLike = {
            "aws:SourceArn" = aws_s3_bucket.access_logs.arn
          }
        }
      }
    ]
  })
}

# Enable server access logging for the deployment bucket
resource "aws_s3_bucket_logging" "lambda_deployment" {
  bucket        = aws_s3_bucket.lambda_deployment.id
  target_bucket = aws_s3_bucket.access_logs.id
  target_prefix = "s3/${var.app_name}-${var.environment}-deployment/"
  depends_on = [
    aws_s3_bucket_policy.lambda_deployment
  ]
}

# Block public access to the bucket
resource "aws_s3_bucket_public_access_block" "lambda_deployment" {
  bucket = aws_s3_bucket.lambda_deployment.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Enable server-side encryption for the S3 bucket
resource "aws_s3_bucket_server_side_encryption_configuration" "lambda_deployment" {
  bucket = aws_s3_bucket.lambda_deployment.id

  rule {
    apply_server_side_encryption_by_default {
      kms_master_key_id = aws_kms_key.main.arn
      sse_algorithm     = "aws:kms"
    }
  }
}



# Network Module
# Network Module
module "network" {
  source = "./modules/network"


  region      = local.current_region
  app_name    = var.app_name
  environment = var.environment
  vpc_cidr    = var.vpc_cidr

  # VPC Flow Logs configuration
  enable_flow_logs            = true
  flow_logs_retention_in_days = var.environment == "prod" ? 30 : 7

  tags = local.tags
}

# IAM Module
module "iam" {
  source = "./modules/iam"

  region        = local.current_region
  app_name      = var.app_name
  environment   = var.environment
  account_id    = data.aws_caller_identity.current.account_id
  db_secret_arn = module.rds.db_secret_arn
  tags          = local.tags

}

# Main KMS Key for all encryption
resource "aws_kms_key" "main" {
  description             = "Main KMS key for ${var.app_name} ${var.environment} environment"
  deletion_window_in_days = var.environment == "prod" ? 30 : 7
  enable_key_rotation     = true
  policy                  = data.aws_iam_policy_document.kms_main_policy.json

  tags = merge({
    Name        = "${var.app_name}-${var.environment}-main-kms-key"
    Environment = var.environment
    ManagedBy   = "terraform"
  }, var.tags)
}

# KMS Key Policy for the main key
data "aws_iam_policy_document" "kms_main_policy" {
  # Allow root account full access
  statement {
    sid    = "Enable IAM User Permissions"
    effect = "Allow"
    principals {
      type        = "AWS"
      identifiers = ["arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"]
    }
    actions   = ["kms:*"]
    resources = ["*"]
  }

  # Allow AWS services to use the key
  statement {
    sid    = "Allow AWS Services to use the key"
    effect = "Allow"
    principals {
      type = "Service"
      identifiers = [
        "rds.amazonaws.com",
        "logs.${data.aws_region.current.name}.amazonaws.com",
        "lambda.amazonaws.com",
        "apigateway.amazonaws.com",
        "sns.amazonaws.com"
      ]
    }
    actions = [
      "kms:Encrypt",
      "kms:Decrypt",
      "kms:ReEncrypt*",
      "kms:GenerateDataKey*",
      "kms:CreateGrant",
      "kms:ListGrants",
      "kms:DescribeKey"
    ]
    resources = ["*"]
  }

  # Allow CloudWatch Logs to use the key with specific conditions
  statement {
    sid    = "Allow CloudWatch Logs to use the key"
    effect = "Allow"
    principals {
      type        = "Service"
      identifiers = ["logs.${data.aws_region.current.name}.amazonaws.com"]
    }
    actions = [
      "kms:Encrypt*",
      "kms:Decrypt*",
      "kms:ReEncrypt*",
      "kms:GenerateDataKey*",
      "kms:Describe*"
    ]
    resources = ["*"]
    condition {
      test     = "ArnLike"
      variable = "kms:EncryptionContext:aws:logs:arn"
      values = [
        "arn:aws:logs:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:*"
      ]
    }
  }

  # Allow SNS to use the key
  statement {
    sid    = "Allow SNS to use the key"
    effect = "Allow"
    principals {
      type        = "Service"
      identifiers = ["sns.amazonaws.com"]
    }
    actions = [
      "kms:GenerateDataKey",
      "kms:Decrypt"
    ]
    resources = ["*"]
  }
}

# KMS Alias for easier reference
resource "aws_kms_alias" "main" {
  name          = "alias/${var.app_name}-${var.environment}-main"
  target_key_id = aws_kms_key.main.key_id
}

# RDS Module
module "rds" {
  source = "./modules/rds"

  # Core configuration
  app_name    = var.app_name
  environment = var.environment

  # Network configuration
  vpc_id               = module.network.vpc_id
  vpc_cidr             = var.vpc_cidr
  db_subnet_group_name = module.network.database_subnet_group_name

  # Security configuration
  lambda_security_group_id = module.lambda.security_group_id

  # Use the main KMS key for encryption
  db_kms_key_arn = aws_kms_key.main.arn

  # Tags
  tags = local.tags
}

# Secret Rotation for RDS
module "secret_rotation" {
  source = "./modules/secret_rotation"

  # Basic configuration
  app_name = var.app_name

  # Secret configuration
  secret_arn = module.rds.db_secret_arn

  # Network configuration
  vpc_id                = module.network.vpc_id
  vpc_cidr              = var.vpc_cidr
  subnet_ids            = module.network.private_subnet_ids
  rds_security_group_id = module.rds.db_security_group_id

  # Lambda configuration
  lambda_package_path = "${path.module}/../dist/secret_rotation.zip"
  lambda_runtime      = "python3.13"
  rotation_days       = 30
}

# API Gateway Module
module "api_gateway" {
  source = "./modules/api_gateway"

  # Required parameters
  app_name    = var.app_name
  environment = var.environment

  # Lambda integration
  lambda_invoke_arn    = module.lambda.invoke_arn
  lambda_function_name = module.lambda.name # Pass the Lambda function name directly
  logs_kms_key_arn     = aws_kms_key.main.arn

  # Domain configuration
  domain_name     = local.domain_name
  cert_domain     = local.cert_domain     # Wildcard certificate for subdomains
  api_domain_name = local.api_domain_name # Full domain name (e.g., api.dev.example.com)

  tags = merge(local.tags, {
    Name = "${var.app_name}-${var.environment}-api"
  })

  # Provider configuration for multi-region support
  providers = {
    aws           = aws
    aws.us-east-1 = aws.us-east-1 # Required for ACM certificate in us-east-1
  }

  depends_on = [
    aws_kms_key.main,
    module.network # Ensure network resources are created first
  ]
}

# Lambda function configuration
module "lambda" {
  source = "./modules/lambda"

  # Basic configuration
  app_name    = var.app_name
  environment = var.environment
  aws_region  = var.aws_region

  # VPC configuration
  vpc_id     = module.network.vpc_id
  vpc_cidr   = module.network.vpc_cidr_block
  subnet_ids = module.network.private_subnet_ids

  # Encryption
  kms_key_arn = aws_kms_key.main.arn

  # Lambda package
  s3_bucket      = aws_s3_bucket.lambda_deployment.bucket
  s3_key         = "${var.environment}/app/latest/app.zip"
  app_local_path = "${path.module}/../dist/app.zip"

  # Layer configuration
  layer_s3_bucket     = aws_s3_bucket.lambda_deployment.bucket
  layer_s3_key        = "${var.environment}/layers/latest/python-dependencies.zip"
  layer_local_path    = "${path.module}/../dist/layers/python-dependencies.zip"
  architectures       = [var.lambda_architecture]
  compatible_runtimes = ["python3.13"]

  # Database configuration
  db_secret_arn        = module.rds.db_secret_arn
  db_security_group_id = module.rds.db_security_group_id

  # API Gateway integration
  api_gateway_execution_arn = module.api_gateway.api_execution_arn

  # Runtime configuration
  handler     = var.lambda_handler
  runtime     = var.lambda_runtime
  memory_size = var.lambda_memory_size
  timeout     = var.lambda_timeout

  # Enable migrations for the first deployment
  run_migrations = var.run_migrations
  log_level      = var.log_level

  # IAM Policy
  lambda_combined_policy_arn = module.iam.lambda_combined_policy_arn

  # Optional features
  enable_xray_tracing = true
  enable_otel_tracing = false # Set to true to enable OpenTelemetry tracing
  create_dlq          = true

  # Extra environment variables
  extra_environment_variables = {
    SESSION_DYNAMODB_TABLE = module.dynamodb.table_name
  }

  # Tags
  tags = merge(local.tags, {
    Name        = "${var.app_name}-${var.environment}-lambda"
    Environment = var.environment
    ManagedBy   = "terraform"
  })
}

# DynamoDB Table for Session Storage
module "dynamodb" {
  source = "./modules/dynamodb"

  # Basic configuration
  table_name                 = "${var.app_name}-${var.environment}-sessions"
  environment                = var.environment
  kms_key_arn                = aws_kms_key.main.arn
  lambda_execution_role_name = module.lambda.lambda_role_name

  tags = merge(local.tags, {
    Name        = "${var.app_name}-${var.environment}-sessions"
    Environment = var.environment
    ManagedBy   = "terraform"
  })
}
