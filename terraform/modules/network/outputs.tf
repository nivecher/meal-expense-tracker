# VPC Outputs
output "vpc_id" {
  description = "The ID of the VPC"
  value       = aws_vpc.main.id
}

output "vpc_cidr_block" {
  description = "The CIDR block of the VPC"
  value       = aws_vpc.main.cidr_block
}

# Subnet Outputs
output "public_subnet_ids" {
  description = "List of public subnet IDs"
  value       = aws_subnet.public[*].id
}

output "private_subnet_ids" {
  description = "List of private subnet IDs"
  value       = aws_subnet.private[*].id
}

output "database_subnet_group_name" {
  description = "Name of the database subnet group"
  value       = try(aws_db_subnet_group.main.name, "")
}

# Security Group Outputs
output "default_security_group_id" {
  description = "The ID of the default security group"
  value       = aws_vpc.main.default_security_group_id
}

# Security groups are now managed by their respective modules

# VPC Endpoint Outputs
output "s3_prefix_list_id" {
  description = "The prefix list ID for the S3 VPC endpoint"
  value       = try(aws_vpc_endpoint.s3.prefix_list_id, "")
}
