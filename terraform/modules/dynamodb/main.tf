# DynamoDB table for Flask session storage
resource "aws_dynamodb_table" "sessions" {
  name         = var.table_name
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "id"
  range_key    = "expires"

  # Enable encryption using customer-managed KMS key
  server_side_encryption {
    enabled     = true
    kms_key_arn = var.kms_key_arn
  }

  # Enable point-in-time recovery
  point_in_time_recovery {
    enabled = true
  }

  # Table attributes
  attribute {
    name = "id"
    type = "S"
  }

  attribute {
    name = "expires"
    type = "N"
  }

  # Enable TTL for session expiration
  ttl {
    attribute_name = "expires"
    enabled        = true
  }

  # Tags
  tags = merge(
    var.tags,
    {
      Name        = var.table_name
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  )
}

# IAM policy for Lambda to access the DynamoDB table
resource "aws_iam_policy" "dynamodb_access" {
  name        = "${var.table_name}-access-policy"
  description = "Policy for Lambda to access ${var.table_name} DynamoDB table"
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:UpdateItem",
          "dynamodb:DeleteItem",
          "dynamodb:Scan",
          "dynamodb:Query"
        ]
        Resource = [
          aws_dynamodb_table.sessions.arn
        ]
      }
    ]
  })
}

# Attach the policy to the Lambda execution role
resource "aws_iam_role_policy_attachment" "lambda_dynamodb_access" {
  role       = var.lambda_execution_role_name
  policy_arn = aws_iam_policy.dynamodb_access.arn
}
