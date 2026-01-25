variable "s3_bucket_name" {
  description = "Name of the S3 bucket for static assets"
  type        = string
}

variable "app_name" {
  description = "Name of the application"
  type        = string
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
}

variable "api_gateway_custom_domain" {
  description = "API Gateway target domain name (AWS-provided regional domain for CloudFront origin)"
  type        = string
}

variable "acm_certificate_arn" {
  description = "ACM certificate ARN for custom domain"
  type        = string
}

variable "route53_zone_id" {
  description = "Route53 zone ID for DNS record"
  type        = string
}

variable "aliases" {
  description = "Alternative domain names for CloudFront distribution"
  type        = list(string)
  default     = []
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}

variable "enable_waf" {
  description = "Enable AWS WAF for CloudFront distribution"
  type        = bool
  default     = true
}

variable "waf_include_common_ruleset" {
  description = "Include AWS Managed Common Rule Set (has standard pricing, not free tier)"
  type        = bool
  default     = false
}
