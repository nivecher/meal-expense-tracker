# Core Configuration
variable "app_name" {
  description = "Name of the application"
  type        = string
}

variable "environment" {
  description = "Deployment environment (dev, staging, prod)"
  type        = string
}

# AWS Configuration
variable "region" {
  description = "AWS region where resources will be created"
  type        = string
}

variable "account_id" {
  description = "AWS account ID"
  type        = string
}

# Database Configuration
variable "db_secret_arn" {
  description = "ARN of the database secret in Secrets Manager"
  type        = string
}

variable "db_instance_identifier" {
  description = "The RDS instance identifier (e.g., mydb-instance-1)"
  type        = string
}

variable "db_username" {
  description = "Database username for IAM authentication"
  type        = string
  default     = "app_user"
}

# Tags
variable "tags" {
  description = "A map of tags to add to all resources"
  type        = map(string)
  default     = {}
}
