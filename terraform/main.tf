# Main Terraform configuration
# This file serves as the entry point for Terraform

# Get the current AWS account ID and region
data "aws_caller_identity" "current" {}
data "aws_region" "current" {}
# Generate application secret key
resource "random_password" "app_secret_key" {
  length           = 50
  special          = true
  override_special = "!@#$%^&*()_+-=[]{}|;:,.<>?"
  min_lower        = 5
  min_numeric      = 5
  min_special      = 5
  min_upper        = 5
}

# Store application secret key in SSM Parameter Store
resource "aws_ssm_parameter" "app_secret_key" {
  name        = "/${var.app_name}/${var.environment}/app/secret_key"
  description = "Application secret key for ${var.app_name} in ${var.environment}"
  type        = "SecureString"
  value       = random_password.app_secret_key.result
  tier        = "Standard" # Changed from Advanced to avoid issues
  data_type   = "text"
  overwrite   = true

  tags = local.tags

  lifecycle {
    ignore_changes = [value]
  }
}

# Main KMS Key for encryption
resource "aws_kms_key" "main" {
  description             = "Main KMS key for ${var.app_name} ${var.environment} environment"
  deletion_window_in_days = var.environment == "prod" ? 30 : 7
  enable_key_rotation     = true
  policy                  = data.aws_iam_policy_document.kms_main_policy.json

  tags = local.tags
}

# KMS Key Policy
data "aws_iam_policy_document" "kms_main_policy" {
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

  statement {
    sid    = "Allow AWS Services to use the key"
    effect = "Allow"
    principals {
      type = "Service"
      identifiers = [
        "logs.${data.aws_region.current.name}.amazonaws.com",
        "lambda.amazonaws.com",
        "apigateway.amazonaws.com",
        "sns.amazonaws.com",
        "s3.amazonaws.com"
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
}

# KMS Alias
resource "aws_kms_alias" "main" {
  name          = "alias/${var.app_name}-${var.environment}-main"
  target_key_id = aws_kms_key.main.key_id
}

# ECR Repository for Lambda container images
module "ecr" {
  source = "./modules/ecr"

  repository_name      = "${var.app_name}-${var.environment}-lambda"
  environment          = var.environment
  kms_key_arn          = aws_kms_key.main.arn
  force_delete         = true
  image_tag_mutability = "MUTABLE" # Allow overwriting 'latest' tag for easier iteration

  tags = local.tags
}

# Database: Using Supabase (external PostgreSQL)
# No Aurora or RDS Proxy needed - Lambda connects via HTTPS over internet
# This eliminates $95/month in infrastructure costs!

# IAM Module (simplified for Supabase - no database secret needed)
module "iam" {
  source = "./modules/iam"

  app_name               = var.app_name
  environment            = var.environment
  region                 = var.aws_region
  account_id             = data.aws_caller_identity.current.account_id
  db_secret_arn          = "" # No Aurora secrets needed - using Supabase
  db_instance_identifier = "" # No Aurora instance
  db_username            = "" # No Aurora username
  tags                   = local.tags
}

# API Gateway Module
module "api_gateway" {
  source = "./modules/api_gateway"

  app_name    = var.app_name
  environment = var.environment

  lambda_invoke_arn    = module.lambda.invoke_arn
  lambda_function_name = module.lambda.name
  logs_kms_key_arn     = aws_kms_key.main.arn

  domain_name     = local.domain_name
  cert_domain     = local.cert_domain
  api_domain_name = local.api_domain_name

  api_cors_allow_origins = [
    "https://${local.api_domain_name}",
    "http://localhost:5000",
    "https://localhost:5000"
  ]
  api_cors_allow_credentials = true
  api_cors_allow_headers     = ["*"]
  api_cors_expose_headers = [
    "Content-Length",
    "Content-Type",
    "X-CSRFToken",
    "Set-Cookie",
    "Location"
  ]

  tags = merge(local.tags, {
    Name = "${var.app_name}-${var.environment}-api"
  })

  providers = {
    aws           = aws
    aws.us-east-1 = aws.us-east-1
  }

  depends_on = [
    aws_kms_key.main
  ]
}

# SNS Topic for notifications
resource "aws_sns_topic" "notifications" {
  name              = "${var.app_name}-${var.environment}-notifications"
  kms_master_key_id = aws_kms_key.main.id

  tags = local.tags

  lifecycle {
    ignore_changes = [
      name,
      tags,
      kms_master_key_id,
    ]
  }
}

# S3 Bucket for receipt storage
module "s3" {
  source = "./modules/s3"

  bucket_name = "${var.app_name}-${var.environment}-receipts"

  kms_key_arn = aws_kms_key.main.arn

  # Lifecycle configuration
  noncurrent_version_expiration_days = 90
  object_expiration_days             = 0 # Never expire by default
  transition_to_ia_days              = 90
  transition_to_glacier_days         = 180

  # Enable access logging for security monitoring
  enable_access_logging = true
  access_log_prefix     = "access-logs/"

  # CORS configuration for web uploads
  cors_rules = [
    {
      allowed_headers = ["*"]
      allowed_methods = ["GET", "PUT", "POST", "DELETE", "HEAD"]
      allowed_origins = [
        "https://${local.api_domain_name}",
        "http://localhost:5000",
        "https://localhost:5000"
      ]
      expose_headers  = ["ETag", "x-amz-request-id"]
      max_age_seconds = 3600
    }
  ]

  tags = local.tags

  depends_on = [
    aws_kms_key.main
  ]
}

# Lambda function configuration
module "lambda" {
  source = "./modules/lambda"

  app_name    = var.app_name
  environment = var.environment
  server_name = local.api_domain_name
  aws_region  = var.aws_region

  app_secret_key_arn = aws_ssm_parameter.app_secret_key.arn

  # Lambda WITHOUT VPC (using Supabase external database)
  # No VPC needed since we're not connecting to Aurora anymore!
  vpc_id     = ""
  vpc_cidr   = ""
  subnet_ids = []

  kms_key_arn = aws_kms_key.main.arn

  # Database configuration - Using Supabase (external PostgreSQL)
  # Lambda will read DATABASE_URL from AWS Secrets Manager
  # No VPC needed since connecting via HTTPS over internet
  db_protocol                 = "postgresql"
  db_secret_arn               = "" # Using Supabase, not Aurora
  db_security_group_id        = "" # No security groups needed outside VPC
  rds_proxy_security_group_id = "" # No RDS Proxy needed
  db_username                 = "" # Not needed for Supabase
  db_host                     = "" # Not needed for Supabase
  db_port                     = "" # Not needed for Supabase
  db_name                     = "" # Not needed for Supabase

  api_gateway_domain_name   = module.api_gateway.api_endpoint
  api_gateway_execution_arn = module.api_gateway.api_execution_arn

  memory_size   = var.lambda_memory_size
  timeout       = var.lambda_timeout
  architectures = [var.lambda_architecture]

  # Package type - use Image for container deployment
  package_type = "Image"

  run_migrations = var.run_migrations
  log_level      = var.log_level

  lambda_combined_policy_arn = module.iam.lambda_combined_policy_arn

  enable_xray_tracing = true
  enable_otel_tracing = false
  create_dlq          = true

  extra_environment_variables = {
    SESSION_TIMEOUT     = "3600"
    ENVIRONMENT        = var.environment
    APP_NAME           = var.app_name
    S3_RECEIPTS_BUCKET = module.s3.bucket_name
  }

  notification_topic_arn = aws_sns_topic.notifications.arn

  tags = merge(local.tags, {
    Name        = "${var.app_name}-${var.environment}-lambda"
    Environment = var.environment
    ManagedBy   = "terraform"
  })

  depends_on = [
    aws_sns_topic.notifications,
    module.s3
  ]
}
