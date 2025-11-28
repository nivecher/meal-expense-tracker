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

# Tags
variable "tags" {
  description = "A map of tags to add to all resources"
  type        = map(string)
  default     = {}
}
