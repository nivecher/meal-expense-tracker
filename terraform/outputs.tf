# API Gateway Outputs
output "api_endpoint" {
  description = "The base URL of the API Gateway"
  value       = module.api_gateway.api_endpoint
}

output "api_execution_arn" {
  description = "The ARN of the API Gateway execution"
  value       = module.api_gateway.api_execution_arn
}

output "api_stage_arn" {
  description = "The ARN of the API Gateway stage"
  value       = module.api_gateway.api_stage_arn
}

# Custom Domain Outputs
output "api_domain_name" {
  description = "The custom domain name of the API Gateway (if configured)"
  value       = module.api_gateway.domain_name
}

output "api_domain_zone_id" {
  description = "The hosted zone ID of the API Gateway custom domain"
  value       = module.api_gateway.domain_zone_id
}

output "api_domain_target_domain" {
  description = "The target domain name of the API Gateway custom domain"
  value       = module.api_gateway.domain_target_domain_name
}

output "api_custom_domain_url" {
  description = "The full URL of the API using the custom domain"
  value       = module.api_gateway.domain_name != null ? "https://${module.api_gateway.domain_name}" : null
}

output "lambda_function_arn" {
  description = "The ARN of the Lambda function"
  value       = module.lambda.lambda_function_arn
}

output "lambda_layer_arn" {
  description = "The ARN of the Lambda layer"
  value       = module.lambda.lambda_layer_arn
}

output "lambda_layer_version_arn" {
  description = "The ARN of the Lambda layer version"
  value       = module.lambda.lambda_layer_version_arn
}

output "lambda_function_name" {
  description = "The name of the Lambda function"
  value       = module.lambda.name
}

output "lambda_invoke_arn" {
  description = "The ARN to be used for invoking the Lambda function from API Gateway"
  value       = module.lambda.invoke_arn
}

# Security Group Outputs
output "lambda_security_group_id" {
  description = "The ID of the Lambda security group"
  value       = module.lambda.security_group_id
}

output "rds_security_group_id" {
  description = "The ID of the RDS security group"
  value       = module.rds.db_security_group_id
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

output "lambda_deployment_bucket_name" {
  description = "The name of the S3 bucket used for Lambda deployment packages"
  value       = data.aws_s3_bucket.lambda_deployment.bucket
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
    lambda   = module.lambda.log_group_name
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
