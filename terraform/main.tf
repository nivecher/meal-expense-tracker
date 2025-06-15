# Main Terraform configuration
# This file serves as the entry point for Terraform

# Get AWS account and region information
data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

# Current region is set via the aws_region variable in variables.tf
locals {
  current_region = var.aws_region
  account_id     = data.aws_caller_identity.current.account_id
}

# KMS Key for all encryption needs
resource "aws_kms_key" "main" {
  description             = "KMS key for ${var.app_name}-${var.environment} encryption"
  deletion_window_in_days = var.environment == "prod" ? 30 : 7
  enable_key_rotation     = true
  policy                  = data.aws_iam_policy_document.kms_key_policy.json

  tags = merge({
    Name        = "${var.app_name}-${var.environment}-key"
    Environment = var.environment
    ManagedBy   = "terraform"
  }, var.tags)
}

# KMS Alias for the key
resource "aws_kms_alias" "main" {
  name          = "alias/${var.app_name}-${var.environment}-key"
  target_key_id = aws_kms_key.main.key_id
}

# IAM policy document for the KMS key
data "aws_iam_policy_document" "kms_key_policy" {
  statement {
    effect = "Allow"
    principals {
      type        = "AWS"
      identifiers = ["arn:aws:iam::${local.account_id}:root"]
    }
    actions   = ["kms:*"]
    resources = ["*"]
  }

  statement {
    effect = "Allow"
    principals {
      type        = "AWS"
      identifiers = ["arn:aws:iam::${local.account_id}:root"]
    }
    actions = [
      "kms:Encrypt",
      "kms:Decrypt",
      "kms:ReEncrypt*",
      "kms:GenerateDataKey*",
      "kms:DescribeKey"
    ]
    resources = ["*"]
  }

  # Allow AWS services to use the key
  statement {
    effect = "Allow"
    principals {
      type        = "Service"
      identifiers = ["logs.${local.current_region}.amazonaws.com"]
    }
    actions = [
      "kms:Encrypt*",
      "kms:Decrypt*",
      "kms:ReEncrypt*",
      "kms:GenerateDataKey*",
      "kms:Describe*"
    ]
    resources = ["*"]
  }

  statement {
    effect = "Allow"
    principals {
      type        = "Service"
      identifiers = ["secretsmanager.amazonaws.com"]
    }
    actions = [
      "kms:CreateGrant",
      "kms:DescribeKey"
    ]
    resources = ["*"]
    condition {
      test     = "StringEquals"
      variable = "kms:CallerAccount"
      values   = [local.account_id]
    }
    condition {
      test     = "StringEquals"
      variable = "kms:ViaService"
      values   = ["secretsmanager.${local.current_region}.amazonaws.com"]
    }
  }
}

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
  logs_kms_key_arn            = aws_kms_key.main.arn

  tags = local.common_tags
}

# IAM Module
module "iam" {
  source = "./modules/iam"

  region        = local.current_region
  app_name      = var.app_name
  environment   = var.environment
  account_id    = data.aws_caller_identity.current.account_id
  db_secret_arn = module.rds.db_secret_arn
  db_identifier = module.rds.db_identifier
  tags          = local.common_tags

  # Ensure KMS key is created before IAM policies that reference it
  depends_on = [aws_kms_key.main]
}

# RDS Module
module "rds" {
  source = "./modules/rds"

  app_name             = var.app_name
  environment          = var.environment
  db_subnet_group_name = module.network.db_subnet_group_name
  db_security_group_id = module.network.db_security_group_id
  db_kms_key_arn       = aws_kms_key.main.arn
  tags                 = local.common_tags

  # Explicitly depend on KMS key creation
  depends_on = [aws_kms_key.main, aws_kms_alias.main]
}

# Lambda Module
module "lambda" {
  source = "./modules/lambda"

  app_name                  = var.app_name
  environment               = var.environment
  lambda_role_arn           = module.iam.lambda_role_arn
  lambda_security_group_ids = [module.network.lambda_security_group_id]
  subnet_ids                = module.network.private_subnet_ids
  memory_size               = var.lambda_memory_size
  timeout                   = var.lambda_timeout
  db_secret_arn             = module.rds.db_secret_arn
  api_gateway_execution_arn = module.api_gateway.api_execution_arn
  logs_kms_key_arn          = aws_kms_key.main.arn
  lambda_kms_key_arn        = aws_kms_key.main.arn
  tags                      = local.common_tags

  # Dead-letter queue configuration
  dead_letter_queue_arn = aws_sns_topic.lambda_dlq.arn

  # Ensure KMS key is created before Lambda function
  depends_on = [
    aws_kms_key.main,
    aws_kms_alias.main,
    aws_sns_topic.lambda_dlq,
    aws_sns_topic_policy.lambda_dlq_policy
  ]
}

# API Gateway Module
module "api_gateway" {
  source = "./modules/api_gateway"

  # Explicitly pass the providers
  providers = {
    aws           = aws           # Default AWS provider
    aws.us-east-1 = aws.us-east-1 # us-east-1 provider for ACM certificates
  }

  region                 = local.current_region
  app_name               = var.app_name
  environment            = var.environment
  lambda_invoke_arn      = module.lambda.invoke_arn
  lambda_function_name   = module.lambda.function_name
  domain_name            = var.cert_domain
  logs_kms_key_arn       = aws_kms_key.main.arn
  tags                   = local.common_tags
  cert_domain            = var.cert_domain
  api_domain_name        = var.api_domain_name
  create_route53_records = var.cert_domain != null && var.api_domain_name != null

  # Ensure KMS key is created before API Gateway
  depends_on = [aws_kms_key.main, aws_kms_alias.main]
}
