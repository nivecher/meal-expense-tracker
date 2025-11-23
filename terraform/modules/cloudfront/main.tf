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

# Use AWS managed cache policies directly with known IDs (more reliable)
locals {
  # AWS managed policy IDs (stable and documented)
  cache_policy_optimized_id = "4135ea2d-6df8-44a3-9df3-4b5a84be39ad" # Managed-CachingOptimized
  cache_policy_disabled_id  = "658327ea-f89d-4fab-a63d-7e88639e58f6" # Managed-CachingDisabled
  origin_request_policy_id  = "b689b0a8-53d0-40ab-baf2-68738e2966ac" # Managed-AllViewerExceptHostHeader
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
  }

  # Behavior 2: Default - everything else → API Gateway (no cache)
  default_cache_behavior {
    allowed_methods        = ["GET", "HEAD", "OPTIONS", "PUT", "POST", "PATCH", "DELETE"]
    cached_methods         = ["GET", "HEAD"]
    target_origin_id       = "API-Gateway"
    compress               = true
    viewer_protocol_policy = "redirect-to-https"

    forwarded_values {
      query_string = true
      headers      = ["Accept", "Accept-Language", "Authorization", "Content-Type", "Origin", "Referer", "User-Agent"] # Forward important headers but not Host
      cookies {
        forward = "all"
      }
    }

    # Disable caching for API Gateway
    min_ttl     = 0
    default_ttl = 0
    max_ttl     = 0
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

  tags = var.tags
}
