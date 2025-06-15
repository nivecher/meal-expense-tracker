output "api_endpoint" {
  description = "The base URL of the API Gateway"
  value       = module.api_gateway.api_endpoint
}

output "api_domain_name" {
  description = "The custom domain name of the API Gateway (if configured)"
  value       = module.api_gateway.domain_name
}

output "lambda_function_name" {
  description = "The name of the Lambda function"
  value       = module.lambda.function_name
}

output "lambda_invoke_arn" {
  description = "The ARN to be used for invoking the Lambda function from API Gateway"
  value       = module.lambda.invoke_arn
}

output "db_endpoint" {
  description = "The connection endpoint for the RDS instance"
  value       = module.rds.db_endpoint
  sensitive   = true
}

output "db_secret_arn" {
  description = "The ARN of the database secret in Secrets Manager"
  value       = module.rds.db_secret_arn
}

output "vpc_id" {
  description = "The ID of the VPC"
  value       = module.network.vpc_id
}

output "private_subnet_ids" {
  description = "List of private subnet IDs"
  value       = module.network.private_subnet_ids
}

output "public_subnet_ids" {
  description = "List of public subnet IDs"
  value       = module.network.public_subnet_ids
}

output "kms_key_arn" {
  description = "The ARN of the KMS key used for encryption"
  value       = aws_kms_key.main.arn
}

output "kms_key_id" {
  description = "The ID of the KMS key used for encryption"
  value       = aws_kms_key.main.key_id
}

output "cloudwatch_log_group_names" {
  description = "Map of CloudWatch Log Group names"
  value = {
    lambda   = module.lambda.cloudwatch_log_group_name
    api_gw   = "/aws/api-gw/${var.app_name}-${var.environment}"
    vpc_flow = "/aws/vpc-flow-logs/${var.app_name}-${var.environment}"
  }
}

output "aws_region" {
  description = "The AWS region"
  value       = data.aws_region.current.name
}

output "aws_account_id" {
  description = "The AWS account ID"
  value       = data.aws_caller_identity.current.account_id
}
