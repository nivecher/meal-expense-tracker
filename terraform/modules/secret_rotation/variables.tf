variable "app_name" {
  description = "The name of the application"
  type        = string
}

variable "secret_arn" {
  description = "The ARN of the secret to rotate"
  type        = string
}

variable "master_secret_arn" {
  description = "The ARN of the master secret with admin privileges"
  type        = string
  default     = ""
}

variable "vpc_id" {
  description = "The ID of the VPC where the Lambda will run"
  type        = string
}

variable "vpc_cidr" {
  description = "The CIDR block of the VPC"
  type        = string
}

variable "subnet_ids" {
  description = "List of subnet IDs where the Lambda will run"
  type        = list(string)
}

variable "rds_security_group_id" {
  description = "The security group ID of the RDS instance"
  type        = string
}

variable "lambda_package_path" {
  description = "Path to the Lambda deployment package"
  type        = string
}

variable "lambda_runtime" {
  description = "The runtime of the Lambda function"
  type        = string
  default     = "python3.13"
}

variable "rotation_days" {
  description = "Number of days between automatic rotations"
  type        = number
  default     = 30
}
