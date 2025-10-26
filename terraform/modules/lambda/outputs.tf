# Lambda Function Outputs
output "lambda_function_arn" {
  description = "The ARN of the Lambda function"
  value       = aws_lambda_function.main.arn
}

# No layer outputs needed for container images

output "invoke_arn" {
  description = "The ARN to be used for invoking Lambda Function from API Gateway"
  value       = aws_lambda_function.main.invoke_arn
}

output "iam_role_arn" {
  description = "The ARN of the IAM role used by the Lambda function"
  value       = aws_iam_role.lambda_role.arn
}

output "name" {
  description = "The name of the Lambda function"
  value       = aws_lambda_function.main.function_name
}

output "qualified_arn" {
  description = "The qualified ARN of the Lambda function"
  value       = aws_lambda_function.main.qualified_arn
}

output "version" {
  description = "Latest published version of your Lambda function"
  value       = aws_lambda_function.main.version
}

# IAM Role Outputs
output "role_arn" {
  description = "The ARN of the IAM role used by the Lambda function"
  value       = aws_iam_role.lambda_role.arn
}

# CloudWatch Log Group Outputs
output "log_group_name" {
  description = "The name of the CloudWatch Log Group for the Lambda function"
  value       = aws_cloudwatch_log_group.lambda.name
}

output "app_secret_key_arn" {
  description = "The ARN of the SSM parameter containing the application secret key"
  value       = data.aws_ssm_parameter.app_secret_key.arn
  sensitive   = true
}

output "lambda_role_name" {
  description = "The name of the IAM role used by the Lambda function"
  value       = aws_iam_role.lambda_role.name
}

output "log_group_arn" {
  description = "The ARN of the CloudWatch Log Group for the Lambda function"
  value       = aws_cloudwatch_log_group.lambda.arn
}

# Dead Letter Queue Outputs
output "dlq_arn" {
  description = "The ARN of the dead letter queue"
  value       = var.create_dlq ? aws_sns_topic.lambda_dlq[0].arn : null
}

# Security Group Outputs (optional if Lambda is not in VPC)
output "security_group_id" {
  description = "The ID of the security group attached to the Lambda function (empty if Lambda is not in VPC)"
  value       = var.vpc_id != "" ? aws_security_group.lambda[0].id : ""
}

# The Dead Letter Queue ARN is now managed in the root module
