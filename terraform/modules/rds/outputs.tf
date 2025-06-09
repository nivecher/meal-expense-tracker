output "db_instance_id" {
  description = "The ID of the RDS instance"
  value       = aws_db_instance.main.id
}

output "db_endpoint" {
  description = "The connection endpoint for the RDS instance"
  value       = aws_db_instance.main.endpoint
}

output "db_name" {
  description = "The name of the database"
  value       = aws_db_instance.main.db_name
}

output "db_username" {
  description = "The master username for the database"
  value       = aws_db_instance.main.username
  sensitive   = true
}

output "db_password" {
  description = "The master password for the database"
  value       = aws_db_instance.main.password
  sensitive   = true
}

output "db_secret_arn" {
  description = "The ARN of the database secret in Secrets Manager"
  value       = aws_secretsmanager_secret.db_credentials.arn
}

output "db_identifier" {
  description = "The identifier of the RDS instance"
  value       = aws_db_instance.main.identifier
}
