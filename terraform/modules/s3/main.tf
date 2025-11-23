# S3 Bucket with Security Best Practices
# This module creates a secure S3 bucket for storing receipt images

resource "aws_s3_bucket" "receipts" {
  bucket = var.bucket_name

  tags = var.tags
}

# Block all public access
resource "aws_s3_bucket_public_access_block" "receipts" {
  bucket = aws_s3_bucket.receipts.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Enable versioning for data protection
resource "aws_s3_bucket_versioning" "receipts" {
  bucket = aws_s3_bucket.receipts.id

  versioning_configuration {
    status = "Enabled"
  }
}

# Enable server-side encryption with KMS
resource "aws_s3_bucket_server_side_encryption_configuration" "receipts" {
  bucket = aws_s3_bucket.receipts.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = var.kms_key_arn
    }
    bucket_key_enabled = true
  }
}

# Enforce HTTPS only (encryption in transit)
resource "aws_s3_bucket_policy" "receipts_ssl" {
  bucket = aws_s3_bucket.receipts.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "DenyInsecureConnections"
        Effect    = "Deny"
        Principal = "*"
        Action    = "s3:*"
        Resource = [
          aws_s3_bucket.receipts.arn,
          "${aws_s3_bucket.receipts.arn}/*"
        ]
        Condition = {
          Bool = {
            "aws:SecureTransport" = "false"
          }
        }
      }
    ]
  })

  depends_on = [
    aws_s3_bucket_public_access_block.receipts
  ]
}

# Lifecycle configuration to manage costs
resource "aws_s3_bucket_lifecycle_configuration" "receipts" {
  bucket = aws_s3_bucket.receipts.id

  rule {
    id     = "delete_old_versions"
    status = "Enabled"

    filter {
      prefix = ""
    }

    noncurrent_version_expiration {
      noncurrent_days = var.noncurrent_version_expiration_days
    }

    dynamic "expiration" {
      for_each = var.object_expiration_days > 0 ? [1] : []
      content {
        days = var.object_expiration_days
      }
    }
  }

  rule {
    id     = "transition_to_ia"
    status = "Enabled"

    filter {
      prefix = ""
    }

    transition {
      days          = var.transition_to_ia_days
      storage_class = "STANDARD_IA"
    }
  }

  rule {
    id     = "transition_to_glacier"
    status = "Enabled"

    filter {
      prefix = ""
    }

    transition {
      days          = var.transition_to_glacier_days
      storage_class = "GLACIER"
    }
  }
}

# Enable access logging (security monitoring)
resource "aws_s3_bucket_logging" "receipts" {
  count = var.enable_access_logging ? 1 : 0

  bucket = aws_s3_bucket.receipts.id

  target_bucket = aws_s3_bucket.logs[0].id
  target_prefix = var.access_log_prefix
}

# Access log bucket (for access logging)
resource "aws_s3_bucket" "logs" {
  count = var.enable_access_logging ? 1 : 0

  bucket = "${var.bucket_name}-logs"

  tags = merge(var.tags, {
    Name = "${var.bucket_name}-logs"
  })
}

resource "aws_s3_bucket_public_access_block" "logs" {
  count = var.enable_access_logging ? 1 : 0

  bucket = aws_s3_bucket.logs[0].id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "logs" {
  count = var.enable_access_logging ? 1 : 0

  bucket = aws_s3_bucket.logs[0].id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = var.kms_key_arn
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_versioning" "logs" {
  count = var.enable_access_logging ? 1 : 0

  bucket = aws_s3_bucket.logs[0].id

  versioning_configuration {
    status = "Enabled"
  }
}

# CORS configuration (if needed for web uploads)
resource "aws_s3_bucket_cors_configuration" "receipts" {
  count = length(var.cors_rules) > 0 ? 1 : 0

  bucket = aws_s3_bucket.receipts.id

  dynamic "cors_rule" {
    for_each = var.cors_rules
    content {
      allowed_headers = cors_rule.value.allowed_headers
      allowed_methods = cors_rule.value.allowed_methods
      allowed_origins = cors_rule.value.allowed_origins
      expose_headers  = cors_rule.value.expose_headers
      max_age_seconds = cors_rule.value.max_age_seconds
    }
  }
}
