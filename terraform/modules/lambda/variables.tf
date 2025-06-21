# ======================
# Core Configuration
# ======================
variable "vpc_cidr" {
  description = "The CIDR block of the VPC"
  type        = string

  validation {
    # This regex validates an IPv4 CIDR block (e.g., 10.0.0.0/16)
    # It allows optional CIDR notation (e.g., 192.168.1.1 or 10.0.0.0/16)
    condition     = can(regex("^(?:[0-9]{1,3}\\.){3}[0-9]{1,3}(?:/[0-9]{1,2})?$", var.vpc_cidr))
    error_message = "Must be a valid IPv4 CIDR block (e.g., 10.0.0.0/16)."
  }
}

variable "app_name" {
  description = "The name of the application"
  type        = string
}

variable "environment" {
  description = "The deployment environment (e.g., dev, staging, prod)"
  type        = string
}

variable "aws_region" {
  description = "The AWS region where resources will be created"
  type        = string
  default     = "us-west-2"
}

# Lambda Function Configuration
variable "handler" {
  description = "The function entrypoint in your code"
  type        = string
  default     = "wsgi.lambda_handler"
}

variable "runtime" {
  description = "The runtime environment for the Lambda function"
  type        = string
  default     = "python3.13"
}

variable "memory_size" {
  description = "The amount of memory in MB your Lambda Function can use"
  type        = number
  default     = 128
}

variable "timeout" {
  description = "The amount of time your Lambda Function has to run in seconds"
  type        = number
  default     = 30
}

variable "run_migrations" {
  description = "Whether to run database migrations on Lambda startup"
  type        = bool
  default     = false
}

variable "log_level" {
  description = "Logging level for the application (DEBUG, INFO, WARNING, ERROR, CRITICAL)"
  type        = string
  default     = "INFO"
}

variable "extra_environment_variables" {
  description = "A map of additional environment variables to pass to the Lambda function"
  type        = map(string)
  default     = {}
}

variable "architectures" {
  description = "Instruction set architecture for your Lambda function"
  type        = list(string)
  default     = ["x86_64"]
}

# Deployment Package
variable "s3_bucket" {
  description = "S3 bucket containing the Lambda deployment package"
  type        = string
}

variable "log_retention_in_days" {
  description = "Number of days to retain Lambda function logs in CloudWatch"
  type        = number
  default     = 30
}

variable "create_dlq" {
  description = "Whether to create a Dead Letter Queue for the Lambda function"
  type        = bool
  default     = false
}

variable "dlq_topic_name" {
  description = "Name of the SNS topic to use for the DLQ"
  type        = string
  default     = ""
}

# Lambda Layer Variables
variable "layer_s3_bucket" {
  description = "S3 bucket where the Lambda layer package will be stored. Leave empty to skip layer creation."
  type        = string
  default     = ""
}

variable "layer_s3_key" {
  description = "S3 key where the Lambda layer package will be stored in the bucket"
  type        = string
  default     = ""
}

variable "layer_local_path" {
  description = "Local filesystem path to the Lambda layer zip file. Required if layer_s3_bucket is set."
  type        = string
  default     = ""
}

variable "app_local_path" {
  description = "Local filesystem path to the Lambda application zip file. Required if app_s3_bucket is set."
  type        = string
  default     = ""
}

variable "compatible_runtimes" {
  description = "List of compatible runtimes for the Lambda layer"
  type        = list(string)
  default     = ["python3.13"]
}

variable "compatible_architectures" {
  description = "List of compatible architectures for the Lambda layer"
  type        = list(string)
  default     = ["x86_64"]
}

variable "s3_key" {
  description = "S3 key of the deployment package"
  type        = string
}

# VPC Configuration
variable "vpc_id" {
  description = "The ID of the VPC where the Lambda function will be deployed"
  type        = string
  default     = ""
}

variable "subnet_ids" {
  description = "List of subnet IDs for the Lambda function when deployed in a VPC"
  type        = list(string)
  default     = []
}

# Database Configuration
variable "db_secret_arn" {
  description = "ARN of the Secrets Manager secret containing the database credentials"
  type        = string
  default     = ""
}

variable "db_security_group_id" {
  description = "The security group ID of the RDS instance"
  type        = string
  default     = ""
}

# API Gateway Integration
variable "api_gateway_execution_arn" {
  description = "The ARN of the API Gateway that will invoke this Lambda"
  type        = string
  default     = ""
}

# Monitoring and Logging
variable "enable_xray_tracing" {
  description = "Enable X-Ray tracing for the Lambda function"
  type        = bool
  default     = false
}

variable "enable_otel_tracing" {
  description = "Enable OpenTelemetry tracing for the Lambda function"
  type        = bool
  default     = false
}

# KMS
variable "kms_key_arn" {
  description = "The ARN of the KMS key to use for encryption"
  type        = string
}

variable "lambda_combined_policy_arn" {
  description = "The ARN of the combined IAM policy to attach to the Lambda role"
  type        = string
}

# Tags
variable "tags" {
  description = "A map of tags to add to all resources"
  type        = map(string)
  default     = {}
}
