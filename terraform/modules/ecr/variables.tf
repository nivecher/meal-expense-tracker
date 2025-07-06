# Core Configuration
variable "repository_name" {
  description = "Name of the ECR repository"
  type        = string
}

variable "environment" {
  description = "Deployment environment (dev, staging, prod)"
  type        = string
}

variable "kms_key_arn" {
  description = "The ARN of the KMS key to use for encryption. If not provided, AWS-managed encryption will be used."
  type        = string
  default     = null
}

variable "force_delete" {
  description = "Whether to force delete the repository even if it contains images"
  type        = bool
  default     = false
}

variable "image_tag_mutability" {
  description = "The tag mutability setting for the repository. Must be one of: MUTABLE or IMMUTABLE"
  type        = string
  default     = "IMMUTABLE"
  validation {
    condition     = var.image_tag_mutability == "" || contains(["MUTABLE", "IMMUTABLE"], var.image_tag_mutability)
    error_message = "The image_tag_mutability must be either 'MUTABLE' or 'IMMUTABLE'."
  }
}

# Lifecycle Policy
variable "max_image_count" {
  description = "Maximum number of images to retain in the repository"
  type        = number
  default     = 10
}

# Tags
variable "tags" {
  description = "A map of tags to add to all resources"
  type        = map(string)
  default     = {}
}
