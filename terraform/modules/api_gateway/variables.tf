# Core Configuration
variable "app_name" {
  description = "Name of the application"
  type        = string
}

variable "environment" {
  description = "Deployment environment (dev, staging, prod)"
  type        = string
}

variable "logs_kms_key_arn" {
  description = "The ARN of the KMS key used for encrypting logs"
  type        = string
}

variable "tags" {
  description = "A map of tags to add to all resources"
  type        = map(string)
  default     = {}
}

# Domain Configuration
variable "domain_name" {
  description = <<-EOT
    The base domain name (e.g., 'example.com') used for:
    1. Looking up the Route53 hosted zone
    2. Creating CORS allowed origins
    3. Deriving the subdomain for the API Gateway custom domain
  EOT
  type        = string
  default     = null

  validation {
    condition     = var.domain_name == null || can(regex("^[a-zA-Z0-9][a-zA-Z0-9-]{1,61}[a-zA-Z0-9](?:\\.[a-zA-Z]{2,})+$", var.domain_name))
    error_message = "The domain_name must be a valid domain name (e.g., 'example.com')"
  }
}

variable "api_domain_name" {
  description = <<-EOT
    The full domain name for the API (e.g., 'api.example.com').
    This is used to:
    1. Create the API Gateway custom domain
    2. Set up the domain name configuration
    3. Create the Route53 record
  EOT
  type        = string
  default     = null

  validation {
    condition     = var.domain_name == null || (var.api_domain_name != null && var.api_domain_name != "")
    error_message = "api_domain_name must be provided if domain_name is provided"
  }

  validation {
    condition     = var.api_domain_name == null || can(regex("^[a-zA-Z0-9][a-zA-Z0-9-]{1,61}[a-zA-Z0-9](?:[.][a-zA-Z0-9-]+)*[.][a-zA-Z]{2,}$", var.api_domain_name))
    error_message = "The api_domain_name must be a valid domain name (e.g., 'api.example.com')"
  }
}

variable "cert_domain" {
  description = <<-EOT
    The domain name the SSL certificate is issued for (e.g., '*.example.com').
    This must match the domain of the ACM certificate that will be used for the API Gateway custom domain.
    For wildcard certificates, use the format '*.example.com'.
  EOT
  type        = string
  default     = null

  validation {
    condition = var.cert_domain == null || (
      can(regex("^\\*\\..+$", var.cert_domain)) &&
      (var.api_domain_name == null ||
        var.cert_domain == var.api_domain_name ||
        (startswith(var.cert_domain, "*.") &&
      endswith(var.api_domain_name, substr(var.cert_domain, 1, length(var.cert_domain)))))
    )
    error_message = "The cert_domain must be a wildcard domain (e.g., '*.example.com')"
  }
}

# Integration Configuration
variable "lambda_invoke_arn" {
  description = "The ARN to invoke the Lambda function (optional)"
  type        = string
  default     = null
}

variable "lambda_function_name" {
  description = "The name of the Lambda function to grant API Gateway permissions to"
  type        = string
  default     = null
}
