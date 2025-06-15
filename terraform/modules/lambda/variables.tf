variable "app_name" {
  description = "Name of the application"
  type        = string
}

variable "environment" {
  description = "Deployment environment (dev, staging, prod)"
  type        = string
}

variable "lambda_role_arn" {
  description = "ARN of the IAM role for the Lambda function"
  type        = string
}

variable "lambda_security_group_ids" {
  description = "List of security group IDs for the Lambda function"
  type        = list(string)
}

variable "subnet_ids" {
  description = "List of subnet IDs for the Lambda function"
  type        = list(string)
}

variable "memory_size" {
  description = "Amount of memory in MB for the Lambda function"
  type        = number
  default     = 256
}

variable "timeout" {
  description = "Timeout in seconds for the Lambda function"
  type        = number
  default     = 30
}

variable "db_secret_arn" {
  description = "ARN of the database secret in Secrets Manager"
  type        = string
}

variable "api_gateway_execution_arn" {
  description = "The ARN of the API Gateway execution"
  type        = string
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

variable "lambda_kms_key_arn" {
  description = "The ARN of the KMS key used to encrypt Lambda environment variables"
  type        = string
}

variable "dead_letter_queue_arn" {
  description = "ARN of the SNS topic to use as a dead-letter queue for the Lambda function. If not provided, no DLQ will be configured."
  type        = string
  default     = null
}
