output "lambda_function_arn" {
  description = "The ARN of the secret rotation Lambda function"
  value       = aws_lambda_function.secret_rotation.arn
}

output "lambda_function_name" {
  description = "The name of the secret rotation Lambda function"
  value       = aws_lambda_function.secret_rotation.function_name
}

output "security_group_id" {
  description = "The ID of the security group for the Lambda function"
  value       = aws_security_group.lambda_sg.id
}
