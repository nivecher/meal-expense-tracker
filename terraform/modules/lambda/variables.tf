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

variable "server_name" {
  description = "The server name for the application (e.g., meal-expense-tracker-dev.us-west-2.elb.amazonaws.com)"
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
  default     = ["arm64", "x86_64"]
}

# Deployment Package
variable "s3_bucket" {
  description = "S3 bucket containing the Lambda deployment package"
  type        = string
}

variable "log_retention_in_days" {
  description = "Number of days to retain Lambda function logs in CloudWatch"
  type        = number
  default     = 7
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
  default     = ["arm64", "x86_64"]
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

  validation {
    condition     = can(regex("^arn:aws:secretsmanager:", var.db_secret_arn)) || var.db_secret_arn == ""
    error_message = "The db_secret_arn must be a valid AWS Secrets Manager ARN or an empty string."
  }
}

variable "db_username" {
  description = "Database username for direct connection in non-prod environments."
  type        = string
  default     = null
}

variable "db_password" {
  description = "Database password for direct connection in non-prod environments."
  type        = string
  default     = null
}

variable "db_security_group_id" {
  description = "The security group ID of the RDS instance that the Lambda function needs to access"
  type        = string

  validation {
    condition     = can(regex("^sg-", var.db_security_group_id)) || var.db_security_group_id == ""
    error_message = "The db_security_group_id must be a valid security group ID starting with 'sg-' or an empty string."
  }
}

variable "app_secret_key_arn" {
  description = "The ARN of the SSM parameter containing the application secret key"
  type        = string
}

variable "db_protocol" {
  description = "Database protocol for direct connection in non-prod environments."
  type        = string
  default     = "postgresql"
}

variable "db_host" {
  description = "Database host for direct connection in non-prod environments."
  type        = string
  default     = null
}

variable "db_port" {
  description = "Database port for direct connection in non-prod environments."
  type        = string
  default     = null
}

variable "db_name" {
  description = "Database name for direct connection in non-prod environments."
  type        = string
  default     = null
}

variable "session_type" {
  description = "The type of session storage to use (e.g., 'dynamodb', 'filesystem')"
  type        = string
  default     = "dynamodb"

  validation {
    condition     = contains(["dynamodb", "dynamodb-boto3", "redis", "memcached"], var.session_type)
    error_message = "Session type must be one of: dynamodb, redis, memcached"
  }
}

variable "session_table_name" {
  description = "The name of the DynamoDB table to use for session storage"
  type        = string
  default     = "flask_sessions"
}

variable "api_gateway_domain_name" {
  description = "The Domain name of the API Gateway that will invoke this Lambda"
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

variable "dynamodb_table_arn" {
  description = "ARN of the DynamoDB table for sessions (ensures dependency)"
  type        = string
  default     = ""
}

# Email Configuration
variable "mail_enabled" {
  description = "Enable email functionality via AWS SES"
  type        = bool
  default     = true
}

variable "mail_default_sender" {
  description = "Default sender email address for AWS SES"
  type        = string
  default     = "noreply@nivecher.com"
}

variable "aws_ses_region" {
  description = "AWS region for SES service"
  type        = string
  default     = "us-east-1"
}

# Tags
variable "tags" {
  description = "A map of tags to add to all resources"
  type        = map(string)
  default     = {}
}
