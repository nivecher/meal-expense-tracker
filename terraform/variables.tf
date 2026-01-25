# ======================
# Core Configuration
# ======================
variable "owner" {
  type        = string
  description = "The owner of the infrastructure (team or individual)"
  default     = "Morgan Davis"
}

variable "assume_role_arn" {
  type        = string
  description = "The ARN of the IAM role to assume when provisioning resources"
  default     = ""
}

variable "app_name" {
  type        = string
  description = "The name of the application"
}

variable "environment" {
  type        = string
  description = "The deployment environment (dev, staging, prod)"
  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be one of: dev, staging, prod"
  }
}

variable "aws_region" {
  type        = string
  description = "The AWS region to deploy to"
  default     = "us-east-1"
}

variable "tags" {
  type        = map(string)
  description = "A map of tags to add to all resources"
  default     = {}
}

# ======================
# Domain Configuration
# ======================
variable "base_domain" {
  type        = string
  default     = "nivecher.com"
  description = "Base domain name for the application"
}

variable "app_subdomain" {
  type        = string
  default     = "meals"
  description = "Subdomain for the main application (e.g., 'meals' for meals.dev.nivecher.com)"
}

variable "api_domain_prefix" {
  type        = string
  default     = "api"
  description = "Prefix for API Gateway domain (e.g., 'api' for api.meals.dev.nivecher.com)"
}

# ======================
# Lambda Configuration
# ======================

variable "lambda_architecture" {
  type        = string
  default     = "arm64"
  description = "Instruction set architecture for Lambda (x86_64 or arm64)"

  validation {
    condition     = contains(["x86_64", "arm64"], var.lambda_architecture)
    error_message = "Lambda architecture must be either x86_64 or arm64"
  }
}

variable "lambda_memory_size" {
  type        = number
  default     = 128
  description = "Amount of memory in MB for Lambda function"

  validation {
    condition     = var.lambda_memory_size >= 128 && var.lambda_memory_size <= 10240 && var.lambda_memory_size % 64 == 0
    error_message = "Lambda memory must be between 128MB and 10240MB in 64MB increments"
  }
}

variable "lambda_timeout" {
  type        = number
  default     = 30
  description = "Timeout in seconds for Lambda function"

  validation {
    condition     = var.lambda_timeout > 0 && var.lambda_timeout <= 900
    error_message = "Lambda timeout must be between 1 and 900 seconds"
  }
}

variable "lambda_reserved_concurrency" {
  type        = number
  default     = null
  description = "Reserved concurrency for the Lambda function (null = unreserved)"
}

variable "lambda_environment_vars" {
  type        = map(string)
  default     = {}
  description = "Additional environment variables for Lambda functions"
}

variable "lambda_handler" {
  type        = string
  default     = "wsgi.lambda_handler"
  description = "Handler function for Lambda function. Points to the WSGI handler in wsgi.py"
}

variable "lambda_runtime" {
  type        = string
  default     = "provided.al2"
  description = "Runtime for Lambda function (provided.al2 for container images)"
}

variable "run_migrations" {
  type        = bool
  default     = true
  description = "Run database migrations on first deployment"
}

variable "log_level" {
  type        = string
  default     = "INFO"
  description = "Logging level for the application (DEBUG, INFO, WARNING, ERROR, CRITICAL)"

  validation {
    condition     = contains(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], var.log_level)
    error_message = "Log level must be one of: DEBUG, INFO, WARNING, ERROR, CRITICAL"
  }
}

# ======================
# Cost Control
# ======================
variable "monthly_budget_amount" {
  type        = number
  description = "Monthly budget amount in USD"
  default     = null
}
