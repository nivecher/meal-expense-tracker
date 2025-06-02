variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "prod"
}

variable "app_name" {
  description = "Application name"
  type        = string
  default     = "meal-expense-tracker"
}

variable "database_url" {
  description = "Database URL for the application"
  type        = string
  sensitive   = true
}

variable "image_tag" {
  description = "Docker image tag for the Lambda function"
  type        = string
}

variable "domain_name" {
  description = "The domain name for the ACM certificate"
  type        = string
}
