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

variable "db_performance_insights_enabled" {
  description = "Enable performance insights for the RDS instance"
  type        = bool
  default     = false # free tier eligible
}

# Network Configuration
variable "vpc_cidr" {
  description = "The CIDR block of the VPC"
  type        = string
}

variable "db_allocated_storage" {
  description = "The allocated storage in GB for the RDS database"
  type        = number
}

variable "db_kms_key_arn" {
  description = "The ARN of the KMS key to use for encrypting the database. If not provided, a default AWS-managed key is used."
  type        = string
  default     = null
}

variable "db_publicly_accessible" {
  description = "Whether the RDS instance should be publicly accessible"
  type        = bool
  default     = true # TODO temporary!!!
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

variable "lambda_iam_role_arn" {
  description = "The ARN of the IAM role that will be allowed to connect to RDS"
  type        = string
  default     = null
}

# Network Access
variable "current_ip" {
  description = "The current public IP address for RDS access"
  type        = string
  default     = ""
}

# Tags
variable "admin_cidr_blocks" {
  description = "List of CIDR blocks that should have admin access to the RDS instance"
  type        = list(string)
  default     = []
}

variable "tags" {
  description = "A map of tags to add to all resources"
  type        = map(string)
  default     = {}
}
