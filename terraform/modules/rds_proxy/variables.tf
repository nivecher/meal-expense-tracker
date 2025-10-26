# RDS Proxy Module Variables

variable "app_name" {
  description = "The name of the application"
  type        = string
}

variable "environment" {
  description = "The deployment environment (dev, staging, prod)"
  type        = string
  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be one of: dev, staging, prod"
  }
}

variable "aws_region" {
  description = "AWS region"
  type        = string
}

variable "tags" {
  description = "A map of tags to add to all resources"
  type        = map(string)
  default     = {}
}

# RDS Proxy Configuration
variable "debug_logging" {
  description = "Enable debug logging for RDS Proxy"
  type        = bool
  default     = false
}

variable "idle_client_timeout" {
  description = "The number of seconds a client connection can be idle before the proxy closes it"
  type        = number
  default     = 1800 # 30 minutes
}

# Connection Pool Configuration
variable "max_connections_percent" {
  description = "The maximum size of the connection pool as a percentage of the max connections for the target database"
  type        = number
  default     = 90
  validation {
    condition     = var.max_connections_percent >= 1 && var.max_connections_percent <= 100
    error_message = "Max connections percent must be between 1 and 100"
  }
}

variable "max_idle_connections_percent" {
  description = "The maximum percentage of connections that can be idle in the connection pool"
  type        = number
  default     = 50
  validation {
    condition     = var.max_idle_connections_percent >= 0 && var.max_idle_connections_percent <= 100
    error_message = "Max idle connections percent must be between 0 and 100"
  }
}

variable "connection_borrow_timeout" {
  description = "The number of seconds for a proxy to wait for a connection to become available in the connection pool"
  type        = number
  default     = 120
}

# Aurora Configuration
variable "aurora_cluster_identifier" {
  description = "Identifier of the Aurora cluster to proxy"
  type        = string
}

variable "aurora_secrets_arn" {
  description = "ARN of the Aurora credentials secret"
  type        = string
}

variable "aurora_security_group_id" {
  description = "Security group ID of the Aurora cluster"
  type        = string
}

# Network Configuration
variable "vpc_id" {
  description = "The ID of the VPC"
  type        = string
}

variable "private_subnet_ids" {
  description = "List of private subnet IDs for RDS Proxy"
  type        = list(string)
}

# Security Configuration
variable "kms_key_arn" {
  description = "ARN of the KMS key for encryption"
  type        = string
}

# Monitoring Configuration
variable "enable_monitoring" {
  description = "Enable CloudWatch monitoring for RDS Proxy"
  type        = bool
  default     = true
}

variable "connection_threshold" {
  description = "Database connections threshold for CloudWatch alarm"
  type        = number
  default     = 80
}

variable "client_connection_threshold" {
  description = "Client connections threshold for CloudWatch alarm"
  type        = number
  default     = 100
}
