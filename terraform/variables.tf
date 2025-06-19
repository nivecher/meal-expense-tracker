# ======================
# Core Configuration
# ======================
variable "owner" {
  type        = string
  description = "The owner of the infrastructure (team or individual)"
  default     = ""
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
# Network Configuration
# ======================
variable "vpc_cidr" {
  type        = string
  description = "The CIDR block for the VPC"
  default     = "10.0.0.0/16"
}

variable "allowed_ip_ranges" {
  type        = list(string)
  description = "List of allowed IP ranges for security group rules"
  default     = []
}

variable "enable_public_access" {
  type        = bool
  description = "Whether to enable public access to resources"
  default     = false
}

# ======================
# Domain Configuration
# ======================
variable "base_domain" {
  type        = string
  default     = "nivecher.com"
  description = "Base domain name for the application"
}

variable "api_subdomain" {
  type        = string
  default     = "meals"
  description = "Subdomain for the API (e.g., 'api' or 'meals')"
}

# ======================
# Lambda Configuration
# ======================
variable "lambda_deployment_bucket" {
  type        = string
  default     = "" # Will be generated if empty
  description = "Name of the S3 bucket for Lambda deployment packages"
}

variable "lambda_architecture" {
  type        = string
  default     = "x86_64"
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
  default     = "python3.13"
  description = "Runtime for Lambda function"
}

# ======================
# Database Configuration
# ======================
variable "db_name" {
  type        = string
  default     = "mealexpensetracker"
  description = "Name of the PostgreSQL database"

  validation {
    condition     = can(regex("^[a-zA-Z_][a-zA-Z0-9_]*$", var.db_name))
    error_message = "Database name must start with a letter or underscore and contain only alphanumeric characters and underscores"
  }
}

variable "db_allocated_storage" {
  type        = number
  default     = 20
  description = "Allocated storage in GB for RDS instance"

  validation {
    condition     = var.db_allocated_storage >= 20 && var.db_allocated_storage <= 65536
    error_message = "Database storage must be between 20GB and 64TB (65536GB)"
  }
}

variable "db_instance_class" {
  type        = string
  default     = "db.t3.micro"
  description = "The instance class for the RDS database"

  validation {
    condition     = can(regex("^db\\.[a-z0-9]+\\.[a-z0-9]+$", var.db_instance_class))
    error_message = "DB instance class must be a valid RDS instance class (e.g., db.t3.micro)"
  }
}

variable "db_backup_retention_period" {
  type        = number
  default     = 7
  description = "The number of days to retain automated backups"

  validation {
    condition     = var.db_backup_retention_period >= 0 && var.db_backup_retention_period <= 35
    error_message = "Backup retention period must be between 0 and 35 days"
  }
}

# ======================
# Feature Flags
# ======================
variable "enable_cloudwatch_logs" {
  type        = bool
  default     = true
  description = "Enable CloudWatch Logs for Lambda functions"
}

variable "enable_lambda_function_url" {
  type        = bool
  default     = null # Will be set based on environment if not specified
  description = "Enable Lambda Function URL (auto-detected by environment if not set)"
}

variable "enable_xray_tracing" {
  type        = bool
  default     = false
  description = "Enable AWS X-Ray distributed tracing for Lambda functions and API Gateway"
}

variable "enable_api_gateway_logging" {
  type        = bool
  default     = true
  description = "Enable detailed CloudWatch logging for API Gateway"
}

variable "enable_encryption_at_rest" {
  type        = bool
  default     = true
  description = "Enable encryption at rest for all resources"
}

variable "enable_encryption_in_transit" {
  type        = bool
  default     = true
  description = "Enable encryption in transit using TLS/SSL"
}

# ======================
# Budget & Monitoring Configuration
# ======================
variable "monthly_budget_amount" {
  type        = string
  default     = "50.00"
  description = "Monthly budget amount in USD (e.g., '50.00')"

  validation {
    condition     = can(regex("^[0-9]+(\\.[0-9]{1,2})?$", var.monthly_budget_amount))
    error_message = "Budget amount must be a valid monetary value (e.g., '50.00')"
  }
}

variable "budget_notification_emails" {
  type        = list(string)
  default     = []
  description = "List of email addresses to receive budget notifications"

  validation {
    condition     = alltrue([for email in var.budget_notification_emails : can(regex("^[^@\\s]+@[^@\\s]+\\.[^@\\s]+$", email))])
    error_message = "One or more email addresses are invalid"
  }
}

variable "enable_cloudwatch_alarms" {
  type        = bool
  default     = true
  description = "Enable CloudWatch alarms for critical metrics"
}

variable "alarm_notification_arns" {
  type        = list(string)
  default     = []
  description = "List of SNS topic ARNs for CloudWatch alarm notifications"

  validation {
    condition     = alltrue([for arn in var.alarm_notification_arns : can(regex("^arn:aws:sns:", arn))])
    error_message = "Alarm notification ARNs must be valid SNS topic ARNs"
  }
}
