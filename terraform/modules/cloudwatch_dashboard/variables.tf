variable "app_name" {
  type        = string
  description = "The name of the application"
}

variable "environment" {
  type        = string
  description = "The deployment environment (dev, staging, prod)"
}

variable "aws_region" {
  type        = string
  description = "The AWS region"
  default     = "us-east-1"
}

variable "lambda_log_group_name" {
  type        = string
  description = "The name of the CloudWatch log group for Lambda"
}

variable "api_gateway_log_group_name" {
  type        = string
  description = "The name of the CloudWatch log group for API Gateway"
}

variable "lambda_function_name" {
  type        = string
  description = "The name of the Lambda function"
}

variable "api_gateway_id" {
  type        = string
  description = "The ID of the API Gateway"
}

variable "tags" {
  type        = map(string)
  description = "A map of tags to add to all resources"
  default     = {}
}
