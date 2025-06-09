# Common tags to be used for all resources
locals {
  common_tags = merge({
    Environment = var.environment
    Application = var.app_name
    ManagedBy   = "Terraform"
  }, var.tags)

  # Common naming prefix
  name_prefix = "${var.app_name}-${var.environment}"

  # Common resource names
  vpc_name                = "${local.name_prefix}-vpc"
  lambda_function_name    = "${local.name_prefix}-function"
  api_gateway_name        = "${local.name_prefix}-api"
  rds_instance_identifier = "${local.name_prefix}-db"
  security_group_name     = "${local.name_prefix}-sg"
  iam_role_name           = "${local.name_prefix}-role"

  # Common resource descriptions
  vpc_description         = "VPC for ${var.app_name} ${var.environment} environment"
  lambda_description      = "Lambda function for ${var.app_name} ${var.environment}"
  api_gateway_description = "API Gateway for ${var.app_name} ${var.environment}"
  rds_description         = "RDS instance for ${var.app_name} ${var.environment}"

  # Common security group descriptions
  lambda_sg_description = "Security group for ${var.app_name} Lambda function"
  rds_sg_description    = "Security group for ${var.app_name} RDS instance"
  api_gw_sg_description = "Security group for ${var.app_name} API Gateway"

  # Common IAM role descriptions
  lambda_role_description = "IAM role for ${var.app_name} Lambda function"

  # Common IAM policy descriptions
  lambda_policy_description = "IAM policy for ${var.app_name} Lambda function"
}
