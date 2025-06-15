variable "app_name" {
  description = "Name of the application"
  type        = string
  default     = "meal-expense-tracker"

  validation {
    condition     = can(regex("^[a-zA-Z][a-zA-Z0-9-]*$", var.app_name))
    error_message = "App name must start with a letter and contain only alphanumeric characters and hyphens."
  }
}

variable "environment" {
  description = "Deployment environment (dev, staging, prod)"
  type        = string
  default     = "dev"

  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be one of: dev, staging, prod"
  }
}

variable "aws_region" {
  description = "AWS region to deploy to"
  type        = string
  default     = "us-east-1"
}

variable "vpc_cidr" {
  description = "CIDR block for the VPC"
  type        = string
  default     = "10.0.0.0/16"
}

# Database configuration is handled in the RDS module
variable "lambda_memory_size" {
  description = "Memory size for Lambda function in MB"
  type        = number
  default     = 256

  validation {
    condition     = var.lambda_memory_size >= 128 && var.lambda_memory_size <= 10240 && floor(var.lambda_memory_size) == var.lambda_memory_size
    error_message = "Lambda memory size must be between 128MB and 10240MB in 1MB increments."
  }
}

variable "cert_domain" {
  description = "Domain name for the SSL certificate (e.g., '*.example.com'). Set to null to disable custom domain."
  type        = string
  default     = null
}

variable "api_domain_name" {
  description = "Custom domain name for the API (e.g., 'api.example.com'). Set to null to disable custom domain."
  type        = string
  default     = null
}

variable "create_route53_records" {
  description = "Whether to create Route53 records for the API domain"
  type        = bool
  default     = true
}

variable "lambda_timeout" {
  description = "Timeout for Lambda function in seconds"
  type        = number
  default     = 30

  validation {
    condition     = var.lambda_timeout >= 1 && var.lambda_timeout <= 900
    error_message = "Lambda timeout must be between 1 and 900 seconds."
  }
}

variable "base_domain_name" {
  description = "Base domain name for the application (e.g., example.com)"
  type        = string
  default     = null
}

variable "tags" {
  description = "A map of tags to add to all resources"
  type        = map(string)
  default     = {}
}
