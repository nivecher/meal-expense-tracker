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

# db_identifier is no longer needed as we use wildcards in the IAM policy
# variable "db_identifier" {
#   description = "Identifier of the RDS database"
#   type        = string
# }

# Tags
variable "tags" {
  description = "A map of tags to add to all resources"
  type        = map(string)
  default     = {}
}
