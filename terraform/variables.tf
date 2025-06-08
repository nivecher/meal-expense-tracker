variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Deployment environment (e.g., dev, staging, prod)"
  type        = string
  default     = "dev"

  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be one of: dev, staging, prod"
  }
}

variable "app_name" {
  description = "Application name"
  type        = string
  default     = "meal-expense-tracker"
}

variable "image_tag" {
  description = "Docker image tag for the Lambda function (e.g., 'latest', 'v1.0.0', or git commit SHA)"
  type        = string

  validation {
    condition     = length(var.image_tag) > 0
    error_message = "Image tag cannot be empty"
  }
}

variable "domain_name" {
  description = "Base domain name for the application (e.g., example.com). This will be used for ACM certificate and API Gateway domain configuration."
  type        = string

  validation {
    condition     = can(regex("^([a-zA-Z0-9]+(-[a-zA-Z0-9]+)*\\.)+[a-zA-Z]{2,}$", var.domain_name))
    error_message = "Invalid domain name format. Must be a valid domain (e.g., example.com)."
  }
}

variable "db_name" {
  description = "The name of the database."
  type        = string
  default     = "meal_expenses"
}

variable "db_username" {
  description = "The username for the database."
  type        = string
  default     = "dbadmin"
}

variable "tags" {
  description = "A map of tags to add to all resources"
  type        = map(string)
  default = {
    "Project"    = "Meal Expense Tracker"
    "Owner"      = "Nivecher"
    "CostCenter" = "MealExpenseTracker"
    "ManagedBy"  = "Terraform"
  }
}
