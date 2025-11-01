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

output "api_gateway_target_domain" {
  description = "The target domain for CloudFront to connect to API Gateway"
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

# Lambda layer output removed - no longer using layers

# Database Outputs (Supabase - external PostgreSQL)
# No Aurora outputs needed - using Supabase
output "database_type" {
  description = "Type of database being used"
  value       = "Supabase (external PostgreSQL)"
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

# S3 Outputs
output "receipts_bucket_id" {
  description = "The ID of the S3 bucket for receipts"
  value       = module.s3.bucket_id
}

output "receipts_bucket_arn" {
  description = "The ARN of the S3 bucket for receipts"
  value       = module.s3.bucket_arn
}

output "receipts_bucket_name" {
  description = "The name of the S3 bucket for receipts"
  value       = module.s3.bucket_name
}

output "receipts_bucket_domain_name" {
  description = "The domain name of the S3 bucket for receipts"
  value       = module.s3.bucket_domain_name
}

output "receipts_bucket_regional_domain_name" {
  description = "The regional domain name of the S3 bucket for receipts"
  value       = module.s3.bucket_regional_domain_name
}

output "logs_bucket_id" {
  description = "The ID of the S3 bucket for access logs"
  value       = module.s3.logs_bucket_id
}

output "logs_bucket_arn" {
  description = "The ARN of the S3 bucket for access logs"
  value       = module.s3.logs_bucket_arn
}

# CloudFront Outputs
output "cloudfront_distribution_id" {
  description = "The ID of the CloudFront distribution"
  value       = module.cloudfront.distribution_id
}

output "cloudfront_distribution_domain_name" {
  description = "The domain name of the CloudFront distribution"
  value       = module.cloudfront.distribution_domain_name
}

output "cloudfront_url" {
  description = "The CloudFront distribution URL"
  value       = module.cloudfront.distribution_url
}

output "static_bucket_name" {
  description = "The name of the S3 bucket for static files"
  value       = module.cloudfront.bucket_name
}
