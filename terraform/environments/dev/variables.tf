# Core Configuration
variable "app_name" {
  description = "Application name"
  type        = string
}

variable "environment" {
  description = "The environment name (e.g., dev, staging, prod)"
  type        = string
}

# AWS Configuration
variable "aws_region" {
  description = "AWS region to deploy resources"
  type        = string
}

variable "common_tags" {
  description = "Common tags to apply to resources"
  type        = map(string)
  default     = {}
}

# Database Configuration
variable "db_instance_class" {
  description = "The instance class of the RDS database"
  type        = string
}

variable "db_allocated_storage" {
  description = "The allocated storage in GB for the RDS database"
  type        = number
}

variable "vpc_cidr" {
  description = "The CIDR block for the VPC"
  type        = string
}

# Security & Access
variable "allowed_ip_ranges" {
  description = "List of allowed IP ranges for accessing the application"
  type        = list(string)
}

# Monitoring & Budgeting
variable "enable_cloudwatch_logs" {
  description = "Whether to enable CloudWatch logging for the application"
  type        = bool
}

variable "monthly_budget_amount" {
  description = "The monthly budget amount in USD for the environment"
  type        = number
}
