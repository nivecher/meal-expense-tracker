# Variable declarations required by this environment module

variable "environment" {
  description = "The environment name (e.g., dev, staging, prod)"
  type        = string
}

variable "aws_region" {
  description = "AWS region to deploy resources"
  type        = string
}

variable "app_name" {
  description = "Application name"
  type        = string
}

variable "common_tags" {
  description = "Common tags to apply to resources"
  type        = map(string)
  default     = {}
}

variable "enable_cloudwatch_logs" {
  type = bool
}

variable "enable_xray_tracing" {
  type = bool
}

variable "enable_cost_alert" {
  type = bool
}

variable "monthly_budget_amount" {
  type = number
}

variable "allowed_ip_ranges" {
  type = list(string)
}

variable "db_instance_class" {
  type = string
}

variable "db_allocated_storage" {
  type = number
}
