output "db_instance_id" {
  description = "The ID of the RDS instance"
  value       = aws_db_instance.main.id
}

output "db_endpoint" {
  description = "The connection endpoint for the RDS instance"
  value       = aws_db_instance.main.endpoint
}

output "db_host" {
  description = "The hostname of the RDS instance"
  value       = aws_db_instance.main.address
}

output "db_port" {
  description = "The port on which the RDS instance accepts connections"
  value       = aws_db_instance.main.port
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

output "db_security_group_id" {
  description = "The ID of the security group for the RDS instance"
  value       = aws_security_group.rds.id
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

output "db_instance_identifier" {
  description = "The identifier of the RDS instance"
  value       = aws_db_instance.main.identifier
}
