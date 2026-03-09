# Main Terraform configuration
# This file serves as the entry point for Terraform

# Get the current AWS account ID and region
data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

# Get the base Route53 zone (e.g., dev.nivecher.com) - must already exist
data "aws_route53_zone" "base" {
  name         = local.domain_name
  private_zone = false
}

# Create Route53 hosted zone for the app subdomain (e.g., meals.dev.nivecher.com)
resource "aws_route53_zone" "app" {
  name = local.app_domain_name

  tags = merge(local.tags, {
    Name = "${var.app_name}-${var.environment}-app-zone"
  })
}

# Delegate the app zone from the base zone
# This creates NS records in the base zone pointing to the app zone's name servers
resource "aws_route53_record" "app_zone_delegation" {
  zone_id = data.aws_route53_zone.base.zone_id
  name    = local.app_domain_name
  type    = "NS"
  ttl     = 172800 # 2 days

  records = aws_route53_zone.app.name_servers

  allow_overwrite = true
}

data "aws_acm_certificate" "main" {
  domain      = local.main_cert_domain
  statuses    = ["ISSUED"]
  most_recent = true
  provider    = aws.us-east-1
}

# Create ACM certificate for API Gateway custom domain
# This certificate covers *.meals.dev.nivecher.com (covers api.meals.dev.nivecher.com)
resource "aws_acm_certificate" "api" {
  domain_name       = local.api_cert_domain
  validation_method = "DNS"
  provider          = aws.us-east-1

  # Ensure the app zone exists before creating the certificate
  depends_on = [aws_route53_zone.app]

  lifecycle {
    create_before_destroy = true
  }

  tags = merge(local.tags, {
    Name = "${var.app_name}-${var.environment}-api-cert"
  })
}

# DNS validation records for API certificate
# These records are created in the existing Route53 zone
resource "aws_route53_record" "api_cert_validation" {
  for_each = {
    for dvo in aws_acm_certificate.api.domain_validation_options : dvo.domain_name => {
      name   = dvo.resource_record_name
      record = dvo.resource_record_value
      type   = dvo.resource_record_type
    }
  }

  allow_overwrite = true
  name            = each.value.name
  records         = [each.value.record]
  ttl             = 60
  type            = each.value.type
  zone_id         = aws_route53_zone.app.zone_id

  # Ensure the app zone is created before creating validation records
  depends_on = [aws_route53_zone.app]
}

# Validate the certificate
resource "aws_acm_certificate_validation" "api" {
  certificate_arn = aws_acm_certificate.api.arn
  validation_record_fqdns = [
    for record in aws_route53_record.api_cert_validation : record.fqdn
  ]
  provider = aws.us-east-1

  timeouts {
    create = "5m"
  }
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
# Lambda connects via HTTPS over internet
# This eliminates $95/month in infrastructure costs!

# IAM Module (using Supabase - no RDS needed)
module "iam" {
  source = "./modules/iam"

  app_name    = var.app_name
  environment = var.environment
  region      = var.aws_region
  account_id  = data.aws_caller_identity.current.account_id
  tags        = local.tags
}

# Lambda function configuration (must come before API Gateway)
module "lambda" {
  source = "./modules/lambda"

  app_name    = var.app_name
  environment = var.environment
  server_name = local.app_domain_name
  aws_region  = var.aws_region

  app_secret_key_arn = aws_ssm_parameter.app_secret_key.arn

  # Lambda WITHOUT VPC (using Supabase external database)
  vpc_id     = ""
  vpc_cidr   = ""
  subnet_ids = []

  kms_key_arn = aws_kms_key.main.arn

  # Note: Database configuration handled via Supabase secrets in Secrets Manager
  # Lambda reads connection details from: meal-expense-tracker/${var.environment}/supabase-connection

  # API Gateway values - use computed local for domain name to avoid circular dependency
  # Domain name is computed from the same inputs API Gateway uses, so they match
  # Note: api_gateway_execution_arn is not actually used in the Lambda module, so we omit it
  api_gateway_domain_name = local.api_gateway_domain_name

  memory_size          = var.lambda_memory_size
  timeout              = var.lambda_timeout
  architectures        = [var.lambda_architecture]
  reserved_concurrency = var.lambda_reserved_concurrency

  package_type = "Image"

  run_migrations = var.run_migrations
  log_level      = var.log_level

  lambda_combined_policy_arn = module.iam.lambda_combined_policy_arn

  enable_xray_tracing = true
  enable_otel_tracing = false
  create_dlq          = true

  extra_environment_variables = {
    SESSION_TIMEOUT    = "3600"
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

# API Gateway Module
module "api_gateway" {
  source = "./modules/api_gateway"

  app_name    = var.app_name
  environment = var.environment

  lambda_invoke_arn    = module.lambda.invoke_arn
  lambda_function_name = module.lambda.name
  logs_kms_key_arn     = aws_kms_key.main.arn

  route53_zone_id   = aws_route53_zone.app.zone_id
  certificate_arn   = aws_acm_certificate_validation.api.certificate_arn
  api_domain_prefix = local.api_domain_prefix
  # Set explicit API domain: api.meals.dev.nivecher.com
  # This is the custom domain that CloudFront will use
  api_domain_name       = "api.${local.app_domain_name}"
  create_route53_record = true # API Gateway handles its own routing

  # CORS configuration: Allow requests from the main domain and localhost
  # CloudFront proxies requests transparently, so browser origin is the main domain
  api_cors_allow_origins     = local.base_cors_origins
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
    aws_kms_key.main,
    module.lambda,
    aws_acm_certificate_validation.api
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
        "https://${local.app_domain_name}",
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

# CloudFront Distribution with Smart Routing
module "cloudfront" {
  source = "./modules/cloudfront"

  s3_bucket_name = "${var.app_name}-${var.environment}-static"
  app_name       = var.app_name
  environment    = var.environment

  api_gateway_custom_domain = module.api_gateway.api_custom_domain

  aliases             = [local.app_domain_name]
  acm_certificate_arn = data.aws_acm_certificate.main.arn
  route53_zone_id     = aws_route53_zone.app.zone_id

  # Disable WAF to save costs ($16/month)
  enable_waf = false

  providers = {
    aws.us-east-1 = aws.us-east-1
  }

  tags = local.tags

  depends_on = [
    module.api_gateway
  ]
}

# CORS Architecture:
# 1. Users access: meals.dev.nivecher.com (CloudFront)
# 2. CloudFront proxies API requests to API Gateway
# 3. Browser origin remains: meals.dev.nivecher.com
# 4. API Gateway CORS allows: meals.dev.nivecher.com ✅
#
# This is the standard, simple approach - no circular dependencies needed!

# CloudWatch Dashboard for debugging
module "cloudwatch_dashboard" {
  source = "./modules/cloudwatch_dashboard"

  app_name    = var.app_name
  environment = var.environment
  aws_region  = var.aws_region

  lambda_log_group_name      = module.lambda.log_group_name
  api_gateway_log_group_name = "/aws/api-gateway/${var.app_name}-${var.environment}"
  lambda_function_name       = module.lambda.name
  api_gateway_id             = module.api_gateway.api_id

  tags = local.tags

  depends_on = [
    module.lambda,
    module.api_gateway
  ]
}

# CloudWatch Alarms for error monitoring
module "cloudwatch_alarms" {
  source = "./modules/cloudwatch_alarms"

  app_name    = var.app_name
  environment = var.environment

  lambda_function_name = module.lambda.name
  api_gateway_name     = "${var.app_name}-${var.environment}"

  sns_topic_arn = aws_sns_topic.notifications.arn

  # Adjust thresholds based on environment
  lambda_error_threshold       = var.environment == "prod" ? 5 : 10
  lambda_throttle_threshold    = var.environment == "prod" ? 1 : 5
  lambda_duration_threshold_ms = var.environment == "prod" ? 10000 : 15000
  lambda_concurrent_threshold  = var.environment == "prod" ? 100 : 200

  api_4xx_error_threshold  = var.environment == "prod" ? 10 : 20
  api_5xx_error_threshold  = var.environment == "prod" ? 1 : 5
  api_latency_threshold_ms = var.environment == "prod" ? 5000 : 8000

  tags = local.tags

  depends_on = [
    module.lambda,
    module.api_gateway,
    aws_sns_topic.notifications
  ]
}
