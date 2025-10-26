# Aurora Serverless Module Outputs

output "cluster_identifier" {
  description = "Aurora cluster identifier"
  value       = aws_rds_cluster.main.cluster_identifier
}

output "cluster_endpoint" {
  description = "Aurora cluster endpoint"
  value       = aws_rds_cluster.main.endpoint
}

output "cluster_endpoint_reader" {
  description = "Aurora cluster reader endpoint"
  value       = aws_rds_cluster.main.reader_endpoint
}

output "cluster_resource_id" {
  description = "Aurora cluster resource ID (for Data API)"
  value       = aws_rds_cluster.main.cluster_resource_id
}

output "cluster_port" {
  description = "Aurora cluster port"
  value       = aws_rds_cluster.main.port
}

output "database_name" {
  description = "Aurora database name"
  value       = aws_rds_cluster.main.database_name
}

output "master_username" {
  description = "Aurora master username"
  value       = aws_rds_cluster.main.master_username
  sensitive   = true
}

output "cluster_arn" {
  description = "Aurora cluster ARN"
  value       = aws_rds_cluster.main.arn
}

output "security_group_id" {
  description = "Aurora security group ID"
  value       = aws_security_group.aurora.id
}

output "secrets_arn" {
  description = "ARN of the Aurora credentials secret"
  value       = aws_secretsmanager_secret.aurora_credentials.arn
}

output "secrets_name" {
  description = "Name of the Aurora credentials secret"
  value       = aws_secretsmanager_secret.aurora_credentials.name
}

output "parameter_group_name" {
  description = "Aurora cluster parameter group name"
  value       = aws_rds_cluster_parameter_group.main.name
}

output "instance_identifier" {
  description = "Aurora cluster instance identifier"
  value       = aws_rds_cluster_instance.main.id
}
