# RDS Proxy Module Outputs

output "proxy_arn" {
  description = "ARN of the RDS Proxy"
  value       = aws_db_proxy.aurora.arn
}

output "proxy_endpoint" {
  description = "Endpoint of the RDS Proxy"
  value       = aws_db_proxy.aurora.endpoint
}

output "proxy_name" {
  description = "Name of the RDS Proxy"
  value       = aws_db_proxy.aurora.name
}

# Proxy port is available via the endpoint (e.g., endpoint splits into host:port)

output "security_group_id" {
  description = "Security group ID for RDS Proxy"
  value       = aws_security_group.rds_proxy.id
}

output "iam_role_arn" {
  description = "IAM role ARN for RDS Proxy"
  value       = aws_iam_role.rds_proxy_role.arn
}

output "target_group_name" {
  description = "Default target group name for RDS Proxy"
  value       = aws_db_proxy_default_target_group.aurora.name
}
