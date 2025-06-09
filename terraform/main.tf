# Main Terraform configuration
# This file serves as the entry point for Terraform

# Get AWS account and region information
data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

# Common tags to be used for all resources
locals {
  common_tags = merge({
    Environment = var.environment
    Application = var.app_name
    ManagedBy   = "Terraform"
  }, var.tags)
}

# Network Module
module "network" {
  source = "./modules/network"

  app_name    = var.app_name
  environment = var.environment
  vpc_cidr    = var.vpc_cidr
  tags        = local.common_tags
}

# IAM Module
module "iam" {
  source = "./modules/iam"

  app_name      = var.app_name
  environment   = var.environment
  region        = data.aws_region.current.name
  account_id    = data.aws_caller_identity.current.account_id
  db_secret_arn = aws_secretsmanager_secret.db_credentials.arn
  db_identifier = module.rds.db_identifier
  tags          = local.common_tags
}

# RDS Module
module "rds" {
  source = "./modules/rds"

  app_name                   = var.app_name
  environment                = var.environment
  vpc_id                     = module.network.vpc_id
  db_subnet_group_name       = module.network.db_subnet_group_name
  db_security_group_id       = module.network.db_security_group_id
  db_instance_class          = var.db_instance_class
  db_allocated_storage       = var.db_allocated_storage
  db_engine                  = var.db_engine
  db_engine_version          = var.db_engine_version
  db_parameter_group_name    = var.db_parameter_group_name
  db_skip_final_snapshot     = var.db_skip_final_snapshot
  db_backup_retention_period = var.db_backup_retention_period
  tags                       = local.common_tags
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
  tags                      = local.common_tags
}

# API Gateway Module
module "api_gateway" {
  source = "./modules/api_gateway"

  app_name            = var.app_name
  environment         = var.environment
  lambda_function_arn = module.lambda.function_arn
  lambda_invoke_arn   = module.lambda.invoke_arn
  domain_name         = var.base_domain_name
  tags                = local.common_tags
}
