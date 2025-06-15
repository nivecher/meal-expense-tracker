variable "region" {
  description = "AWS region where resources will be created"
  type        = string
}

variable "app_name" {
  description = "Name of the application"
  type        = string
}

variable "environment" {
  description = "Deployment environment (dev, staging, prod)"
  type        = string
}

variable "lambda_invoke_arn" {
  description = "The ARN to invoke the Lambda function"
  type        = string
}

variable "domain_name" {
  description = "Optional custom domain name for the API"
  type        = string
  default     = null
}

variable "tags" {
  description = "A map of tags to add to all resources"
  type        = map(string)
  default     = {}
}

variable "logs_kms_key_arn" {
  description = "The ARN of the KMS key to use for encrypting CloudWatch Logs"
  type        = string
}

variable "cert_domain" {
  description = "Domain name for the SSL certificate (e.g., '*.example.com')"
  type        = string
  default     = "*.nivecher.com"
}

variable "api_domain_name" {
  description = "Custom domain name for the API (e.g., 'api.example.com')"
  type        = string
  default     = "meals.nivecher.com"
}

variable "create_route53_records" {
  description = "Whether to create Route53 records for the API domain"
  type        = bool
  default     = true
}

variable "lambda_function_name" {
  description = "The name of the Lambda function to allow API Gateway to invoke"
  type        = string
}
