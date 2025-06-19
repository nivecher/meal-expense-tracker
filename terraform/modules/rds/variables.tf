# Core Configuration
variable "app_name" {
  description = "Name of the application"
  type        = string
}

variable "environment" {
  description = "Deployment environment (dev, staging, prod)"
  type        = string
}

# Network Configuration
variable "vpc_id" {
  description = "The ID of the VPC where the RDS will be deployed"
  type        = string
}

variable "db_subnet_group_name" {
  description = "Name of the DB subnet group"
  type        = string
}

# Network Configuration
variable "vpc_cidr" {
  description = "The CIDR block of the VPC"
  type        = string
}

variable "db_kms_key_arn" {
  description = "The ARN of the KMS key to use for encrypting the database. If not provided, a default AWS-managed key is used."
  type        = string
  default     = null
}

# VPC Endpoint Configuration
variable "secrets_manager_prefix_list_id" {
  description = "The prefix list ID for the Secrets Manager VPC endpoint"
  type        = string
  default     = ""
}

variable "cloudwatch_logs_prefix_list_id" {
  description = "The prefix list ID for the CloudWatch Logs VPC endpoint"
  type        = string
  default     = ""
}

# Tags
variable "tags" {
  description = "A map of tags to add to all resources"
  type        = map(string)
  default     = {}
}
