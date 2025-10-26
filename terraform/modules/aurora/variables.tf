# Aurora Serverless Module Variables

variable "app_name" {
  description = "The name of the application"
  type        = string
}

variable "environment" {
  description = "The deployment environment (dev, staging, prod)"
  type        = string
  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be one of: dev, staging, prod"
  }
}

variable "tags" {
  description = "A map of tags to add to all resources"
  type        = map(string)
  default     = {}
}

variable "backup_retention_period" {
  description = "Number of days to retain backups"
  type        = number
  default     = 7
  validation {
    condition     = var.backup_retention_period >= 1 && var.backup_retention_period <= 35
    error_message = "Backup retention period must be between 1 and 35 days"
  }
}

variable "deletion_protection" {
  description = "Enable deletion protection for the Aurora cluster"
  type        = bool
  default     = false
}

variable "skip_final_snapshot" {
  description = "Skip creating a final snapshot when the cluster is deleted"
  type        = bool
  default     = true
}

# Database Configuration
variable "db_username" {
  description = "Master username for the Aurora database"
  type        = string
  default     = "postgres"
}

variable "db_password" {
  description = "Master password for the Aurora database"
  type        = string
  sensitive   = true
}

variable "db_name" {
  description = "Name of the default database in the Aurora cluster"
  type        = string
  default     = "postgres"
}

# Network Configuration
variable "vpc_id" {
  description = "The ID of the VPC where Aurora will be deployed"
  type        = string
}

variable "db_subnet_group_name" {
  description = "Name of the DB subnet group for Aurora"
  type        = string
}

variable "lambda_security_group_id" {
  description = "Security group ID of the Lambda functions that need to access Aurora"
  type        = string
  default     = ""
}

# Security Configuration
variable "kms_key_arn" {
  description = "ARN of the KMS key for Aurora encryption"
  type        = string
}

# Monitoring Configuration
variable "enable_cloudwatch_alarms" {
  description = "Enable CloudWatch alarms for Aurora monitoring"
  type        = bool
  default     = true
}

variable "cpu_threshold" {
  description = "CPU utilization threshold for CloudWatch alarm"
  type        = number
  default     = 80
}

variable "connections_threshold" {
  description = "Database connections threshold for CloudWatch alarm"
  type        = number
  default     = 50
}
