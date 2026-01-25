# CloudFront Distribution with Dual Origins
# Routes /static/* to S3 and everything else to API Gateway

# S3 Bucket for static assets
resource "aws_s3_bucket" "static" {
  bucket = var.s3_bucket_name

  tags = var.tags
}

# Public access block configuration for CloudFront with OAC
# The bucket is secured via:
# 1. Origin Access Control (OAC) - only CloudFront can access the bucket
# 2. Bucket policy restricts access to CloudFront service only
# 3. All public access is blocked - access only through CloudFront
# OAC works with private buckets as long as the bucket policy allows CloudFront access
resource "aws_s3_bucket_public_access_block" "static" {
  bucket = aws_s3_bucket.static.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Origin Access Control for S3
resource "aws_cloudfront_origin_access_control" "static" {
  name                              = "${var.app_name}-${var.environment}-static-oac-v2"
  description                       = "Origin Access Control for ${var.s3_bucket_name}"
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

# S3 Bucket Policy for CloudFront
# Note: OAC provides security, strict SourceArn condition avoided to prevent circular dependency
resource "aws_s3_bucket_policy" "static" {
  bucket = aws_s3_bucket.static.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AllowCloudFrontAccess"
        Effect = "Allow"
        Principal = {
          Service = "cloudfront.amazonaws.com"
        }
        Action   = "s3:GetObject"
        Resource = "${aws_s3_bucket.static.arn}/*"
        # OAC provides access control, no need for SourceArn condition here
      }
    ]
  })
}

# S3 Bucket for CloudFront access logs
# CloudFront writes logs via bucket policy (service principal), not public ACLs
resource "aws_s3_bucket" "logs" {
  bucket = "${var.app_name}-${var.environment}-cloudfront-logs"

  tags = merge(var.tags, {
    Name = "${var.app_name}-${var.environment}-cloudfront-logs"
  })
}

# Enable versioning for the logs bucket
# Note: MFA delete must be enabled separately using the enable_s3_mfa_delete.sh script
# This is because AWS requires MFA authentication during the enable operation,
# which cannot be automated in Terraform. Enable versioning first, then run the script.
resource "aws_s3_bucket_versioning" "logs" {
  bucket = aws_s3_bucket.logs.id

  versioning_configuration {
    status     = "Enabled"
    mfa_delete = "Disabled" # Enable via enable_s3_mfa_delete.sh script after bucket creation
  }
}

# Public access block for logs bucket
# CloudFront log delivery requires ACLs to be enabled on the bucket.
# Keep public policies blocked, but allow ACL usage for log delivery.
resource "aws_s3_bucket_public_access_block" "logs" {
  bucket = aws_s3_bucket.logs.id

  block_public_acls       = false
  block_public_policy     = true
  ignore_public_acls      = false
  restrict_public_buckets = true
}

# Bucket ownership controls for CloudFront logging
# CloudFront logging requires ACLs to be enabled
# We use BucketOwnerPreferred to allow ACLs while defaulting to bucket owner
resource "aws_s3_bucket_ownership_controls" "logs" {
  bucket = aws_s3_bucket.logs.id

  rule {
    object_ownership = "BucketOwnerPreferred"
  }

  depends_on = [
    aws_s3_bucket_public_access_block.logs
  ]
}

# Enable ACLs on the bucket for CloudFront logging
# The log-delivery-write ACL is specifically designed for CloudFront log delivery
resource "aws_s3_bucket_acl" "logs" {
  bucket = aws_s3_bucket.logs.id
  acl    = "log-delivery-write"

  depends_on = [
    aws_s3_bucket_ownership_controls.logs
  ]
}

# Server-side encryption for logs bucket
resource "aws_s3_bucket_server_side_encryption_configuration" "logs" {
  bucket = aws_s3_bucket.logs.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# Lifecycle configuration to manage old log versions
# Automatically deletes non-current versions after 90 days to manage costs
resource "aws_s3_bucket_lifecycle_configuration" "logs" {
  bucket = aws_s3_bucket.logs.id

  rule {
    id     = "delete_old_versions"
    status = "Enabled"

    filter {
      prefix = ""
    }

    noncurrent_version_expiration {
      noncurrent_days = 90
    }
  }

  depends_on = [
    aws_s3_bucket_versioning.logs
  ]
}

# Bucket policy to allow CloudFront to write logs
# Note: Policy allows CloudFront service to write logs with bucket-owner-full-control ACL
# This is secure as the bucket is private and only CloudFront service can write
resource "aws_s3_bucket_policy" "logs" {
  bucket = aws_s3_bucket.logs.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AllowCloudFrontLogging"
        Effect = "Allow"
        Principal = {
          Service = "cloudfront.amazonaws.com"
        }
        Action   = "s3:PutObject"
        Resource = "${aws_s3_bucket.logs.arn}/*"
        Condition = {
          StringEquals = {
            "s3:x-amz-acl" = "bucket-owner-full-control"
          }
        }
      }
    ]
  })

  depends_on = [
    aws_s3_bucket_ownership_controls.logs
  ]
}

# Custom cache policy that truly disables caching for dynamic content
# When TTL is 0, CloudFront disables caching and forwards all headers/cookies/query strings
resource "aws_cloudfront_cache_policy" "no_cache" {
  name        = "${var.app_name}-${var.environment}-no-cache"
  comment     = "No caching policy for dynamic content from API Gateway"
  default_ttl = 0
  max_ttl     = 0
  min_ttl     = 0

  parameters_in_cache_key_and_forwarded_to_origin {
    # When caching is disabled (TTL=0), compression settings are not allowed
    # CloudFront automatically forwards all requests to origin without caching

    # When caching is disabled (TTL=0), use "none" to forward all cookies
    # Cannot use "all" when TTL is 0
    cookies_config {
      cookie_behavior = "none"
    }

    # When caching is disabled (TTL=0), use "none" to forward all headers
    # Cannot use whitelist when TTL is 0
    headers_config {
      header_behavior = "none"
    }

    # When caching is disabled (TTL=0), use "none" to forward all query strings
    # Cannot use "all" when TTL is 0
    query_strings_config {
      query_string_behavior = "none"
    }
  }
}

# Use AWS managed cache policies directly with known IDs (more reliable)
locals {
  # AWS managed policy IDs (stable and documented)
  cache_policy_optimized_id = "4135ea2d-6df8-44a3-9df3-4b5a84be39ad"  # Managed-CachingOptimized
  cache_policy_disabled_id  = aws_cloudfront_cache_policy.no_cache.id # Custom no-cache policy
  origin_request_policy_id  = "b689b0a8-53d0-40ab-baf2-68738e2966ac"  # Managed-AllViewerExceptHostHeader
}

# Use AWS managed origin request policy instead of custom one
# Managed-AllViewerExceptHostHeader forwards all headers (including Authorization)
# except Host, which is exactly what we need for API Gateway custom domains
# This policy also forwards all cookies and query strings

# WAF Web ACL for CloudFront (using free tier options)
# Bot Control managed rule group: 10M requests/month free
resource "aws_wafv2_web_acl" "cloudfront" {
  count    = var.enable_waf ? 1 : 0
  name     = "${var.app_name}-${var.environment}-cloudfront-waf"
  scope    = "CLOUDFRONT"
  provider = aws.us-east-1 # WAF for CloudFront must be in us-east-1

  default_action {
    allow {}
  }

  # Bot Control managed rule group (FREE: 10M requests/month)
  # This helps protect against automated traffic and bots
  rule {
    name     = "AWSManagedRulesBotControlRuleSet"
    priority = 1

    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesBotControlRuleSet"
        vendor_name = "AWS"
      }
    }

    override_action {
      none {}
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "BotControlRule"
      sampled_requests_enabled   = true
    }
  }

  # AWS Managed Common Rule Set (basic protection)
  # Note: This has standard pricing ($1/month + $0.60 per million requests)
  # Only include if you need additional protection beyond Bot Control
  dynamic "rule" {
    for_each = var.waf_include_common_ruleset ? [1] : []
    content {
      name     = "AWSManagedRulesCommonRuleSet"
      priority = 2

      statement {
        managed_rule_group_statement {
          name        = "AWSManagedRulesCommonRuleSet"
          vendor_name = "AWS"
        }
      }

      override_action {
        none {}
      }

      visibility_config {
        cloudwatch_metrics_enabled = true
        metric_name                = "CommonRuleSet"
        sampled_requests_enabled   = true
      }
    }
  }

  visibility_config {
    cloudwatch_metrics_enabled = true
    metric_name                = "${var.app_name}-${var.environment}-waf"
    sampled_requests_enabled   = true
  }

  tags = var.tags
}

# CloudFront Response Headers Policy for Security Headers
# This adds defense-in-depth by setting security headers at the edge
resource "aws_cloudfront_response_headers_policy" "security" {
  name = "${var.app_name}-${var.environment}-security-headers"

  security_headers_config {
    content_type_options {
      override = true
    }
    frame_options {
      frame_option = "DENY"
      override     = true
    }
    referrer_policy {
      referrer_policy = "strict-origin-when-cross-origin"
      override        = true
    }
    strict_transport_security {
      access_control_max_age_sec = 31536000
      include_subdomains         = true
      override                   = true
    }
  }

  custom_headers_config {
    items {
      header   = "Permissions-Policy"
      value    = "geolocation=(self), microphone=(), camera=()"
      override = true
    }
  }
}

# CloudFront Distribution
resource "aws_cloudfront_distribution" "main" {
  enabled             = true
  is_ipv6_enabled     = true
  default_root_object = "index.html"
  staging             = false
  comment             = "Smart router for ${var.app_name} ${var.environment} - API Gateway fixed"

  # Origin 1: S3 for static files
  origin {
    domain_name              = aws_s3_bucket.static.bucket_regional_domain_name
    origin_id                = "S3-Static"
    origin_access_control_id = aws_cloudfront_origin_access_control.static.id
  }

  # Origin 2: API Gateway for dynamic content
  # Use API Gateway custom domain's target domain (AWS-provided regional domain)
  # This is the recommended approach - stable and optimized for custom domains
  origin {
    domain_name = var.api_gateway_custom_domain
    origin_id   = "API-Gateway"

    custom_origin_config {
      http_port              = 443
      https_port             = 443
      origin_protocol_policy = "https-only"
      origin_ssl_protocols   = ["TLSv1.2"]
    }
  }

  # Behavior 1: /static/* → S3 (cached for 1 year)
  ordered_cache_behavior {
    path_pattern           = "/static/*"
    allowed_methods        = ["GET", "HEAD", "OPTIONS"]
    cached_methods         = ["GET", "HEAD"]
    target_origin_id       = "S3-Static"
    compress               = true
    viewer_protocol_policy = "redirect-to-https"

    cache_policy_id = "4135ea2d-6df8-44a3-9df3-4b5a84be39ad" # Managed-CachingOptimized

    # Add security headers policy
    response_headers_policy_id = aws_cloudfront_response_headers_policy.security.id
  }

  # Behavior 2: Default - everything else → API Gateway (no cache)
  default_cache_behavior {
    allowed_methods        = ["GET", "HEAD", "OPTIONS", "PUT", "POST", "PATCH", "DELETE"]
    cached_methods         = ["GET", "HEAD"]
    target_origin_id       = "API-Gateway"
    compress               = true
    viewer_protocol_policy = "redirect-to-https"

    # Use cache policy and origin request policy (required for HTTP API Gateway)
    cache_policy_id            = local.cache_policy_disabled_id # Managed-CachingDisabled
    origin_request_policy_id   = local.origin_request_policy_id # Managed-AllViewerExceptHostHeader
    response_headers_policy_id = aws_cloudfront_response_headers_policy.security.id
  }

  # Custom error responses for SPA
  custom_error_response {
    error_code            = 403
    response_code         = 404
    response_page_path    = "/index.html"
    error_caching_min_ttl = 300
  }

  custom_error_response {
    error_code            = 404
    response_code         = 404
    response_page_path    = "/index.html"
    error_caching_min_ttl = 300
  }

  # Custom error responses for 5xx errors
  # These pass through origin responses without caching to ensure users see
  # the backend's error pages (HTML for web, JSON for API) rather than cached errors
  custom_error_response {
    error_code            = 500
    error_caching_min_ttl = 0
  }

  custom_error_response {
    error_code            = 502
    error_caching_min_ttl = 0
  }

  custom_error_response {
    error_code            = 503
    error_caching_min_ttl = 0
  }

  custom_error_response {
    error_code            = 504
    error_caching_min_ttl = 0
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  # Viewer certificate (for custom domain)
  viewer_certificate {
    acm_certificate_arn      = var.acm_certificate_arn
    ssl_support_method       = "sni-only"
    minimum_protocol_version = "TLSv1.2_2021"
  }

  # Custom domain
  aliases = var.aliases

  # WAF Web ACL association (if enabled)
  web_acl_id = var.enable_waf ? aws_wafv2_web_acl.cloudfront[0].arn : null

  # Access logging configuration
  logging_config {
    bucket          = aws_s3_bucket.logs.bucket_domain_name
    include_cookies = false
    prefix          = "cloudfront-access-logs/"
  }

  tags = var.tags
}
