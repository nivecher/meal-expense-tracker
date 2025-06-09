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
