output "table_name" {
  description = "Name of the DynamoDB table"
  value       = aws_dynamodb_table.sessions.name
}

output "table_arn" {
  description = "ARN of the DynamoDB table"
  value       = aws_dynamodb_table.sessions.arn
}
