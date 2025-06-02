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

variable "secret_key" {
  description = "Secret key for Flask application"
  type        = string
  sensitive   = true
}

variable "image_tag" {
  description = "Docker image tag for the Lambda function"
  type        = string
}

variable "certificate_arn" {
  description = "ARN of the ACM certificate for HTTPS"
  type        = string
}

variable "domain_name" {
  description = "The domain name for the ACM certificate"
  type        = string
}

variable "route53_zone_id" {
  description = "The Route 53 hosted zone ID for DNS validation"
  type        = string
}
