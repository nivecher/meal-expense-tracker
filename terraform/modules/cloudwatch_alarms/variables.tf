variable "app_name" {
  type        = string
  description = "The name of the application"
}

variable "environment" {
  type        = string
  description = "The deployment environment (dev, staging, prod)"
}

variable "lambda_function_name" {
  type        = string
  description = "The name of the Lambda function"
}

variable "api_gateway_name" {
  type        = string
  description = "The name of the API Gateway"
}

variable "sns_topic_arn" {
  type        = string
  description = "The ARN of the SNS topic for alarm notifications"
  default     = null
}

variable "lambda_error_threshold" {
  type        = number
  description = "Threshold for Lambda error count (errors per 5 minutes)"
  default     = 5
}

variable "lambda_throttle_threshold" {
  type        = number
  description = "Threshold for Lambda throttle count (throttles per 5 minutes)"
  default     = 1
}

variable "lambda_duration_threshold_ms" {
  type        = number
  description = "Threshold for Lambda duration in milliseconds"
  default     = 10000
}

variable "lambda_concurrent_threshold" {
  type        = number
  description = "Threshold for Lambda concurrent executions"
  default     = 100
}

variable "api_4xx_error_threshold" {
  type        = number
  description = "Threshold for API Gateway 4XX errors (errors per 5 minutes)"
  default     = 10
}

variable "api_5xx_error_threshold" {
  type        = number
  description = "Threshold for API Gateway 5XX errors (errors per 5 minutes)"
  default     = 1
}

variable "api_latency_threshold_ms" {
  type        = number
  description = "Threshold for API Gateway latency in milliseconds"
  default     = 5000
}

variable "tags" {
  type        = map(string)
  description = "A map of tags to add to all resources"
  default     = {}
}
