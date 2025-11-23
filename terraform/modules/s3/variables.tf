variable "bucket_name" {
  description = "Name of the S3 bucket for receipts"
  type        = string
}

variable "kms_key_arn" {
  description = "ARN of the KMS key for encryption"
  type        = string
}

variable "tags" {
  description = "Tags to apply to the bucket"
  type        = map(string)
  default     = {}
}

variable "noncurrent_version_expiration_days" {
  description = "Number of days after which non-current versions are deleted"
  type        = number
  default     = 90
}

variable "object_expiration_days" {
  description = "Number of days after which objects are deleted (0 to disable)"
  type        = number
  default     = 0 # Never expire by default
}

variable "transition_to_ia_days" {
  description = "Number of days before transitioning to Standard-IA storage class"
  type        = number
  default     = 90
}

variable "transition_to_glacier_days" {
  description = "Number of days before transitioning to Glacier storage class"
  type        = number
  default     = 180
}

variable "enable_access_logging" {
  description = "Enable S3 access logging"
  type        = bool
  default     = true
}

variable "access_log_prefix" {
  description = "Prefix for access log objects"
  type        = string
  default     = "access-logs/"
}

variable "cors_rules" {
  description = "CORS rules for the bucket"
  type = list(object({
    allowed_headers = list(string)
    allowed_methods = list(string)
    allowed_origins = list(string)
    expose_headers  = list(string)
    max_age_seconds = number
  }))
  default = []
}
