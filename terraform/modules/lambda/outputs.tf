output "function_name" {
  description = "The name of the Lambda function"
  value       = aws_lambda_function.main.function_name
}

output "function_arn" {
  description = "The ARN of the Lambda function"
  value       = aws_lambda_function.main.arn
}

output "invoke_arn" {
  description = "The ARN to be used for invoking the Lambda function from API Gateway"
  value       = aws_lambda_function.main.invoke_arn
}

output "cloudwatch_log_group_name" {
  description = "The name of the CloudWatch Log Group for the Lambda function"
  value       = aws_cloudwatch_log_group.lambda.name
}

output "cloudwatch_log_group_arn" {
  description = "The ARN of the CloudWatch Log Group for the Lambda function"
  value       = aws_cloudwatch_log_group.lambda.arn
}

# The Dead Letter Queue ARN is now managed in the root module
