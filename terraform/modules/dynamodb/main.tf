# DynamoDB table for Flask session storage
resource "aws_dynamodb_table" "sessions" {
  name         = var.table_name
  billing_mode = "PAY_PER_REQUEST" # Use on-demand billing for better cost optimization
  hash_key     = "id"
  # Note: Flask-Session only requires a primary key "id", no range key needed

  # No read/write capacity needed for PAY_PER_REQUEST billing mode

  # Enable encryption using customer-managed KMS key
  server_side_encryption {
    enabled     = true
    kms_key_arn = var.kms_key_arn
  }

  # Enable point-in-time recovery for data protection
  point_in_time_recovery {
    enabled = true
  }

  # Table attributes - Flask-Session only requires 'id' as primary key
  attribute {
    name = "id"
    type = "S"
  }

  # Enable TTL for automatic session cleanup
  # Flask-Session uses 'ttl' attribute for expiration
  ttl {
    attribute_name = "ttl"
    enabled        = true
  }

  # Tags
  tags = merge(
    var.tags,
    {
      Name        = var.table_name
      Environment = var.environment
      ManagedBy   = "terraform"
      Purpose     = "session-storage"
    }
  )
}

# Note: Auto-scaling is not needed for PAY_PER_REQUEST billing mode
# DynamoDB automatically scales based on demand



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
