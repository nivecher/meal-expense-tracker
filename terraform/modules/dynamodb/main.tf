# DynamoDB table for Flask session storage
resource "aws_dynamodb_table" "sessions" {
  name         = var.table_name
  billing_mode = "PROVISIONED" # TODO Set to PAY_PER_REQUEST for auto-scaling
  hash_key     = "id"
  range_key    = "expires"

  # Set read/write capacity based on environment
  read_capacity  = var.environment == "prod" ? 5 : 1
  write_capacity = var.environment == "prod" ? 5 : 1

  # Enable encryption using customer-managed KMS key
  server_side_encryption {
    enabled     = true
    kms_key_arn = var.kms_key_arn
  }

  # Enable point-in-time recovery for data protection
  point_in_time_recovery {
    enabled = true
  }

  # Enable continuous backups
  lifecycle {
    ignore_changes = [read_capacity, write_capacity]
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

  # Global secondary index for querying expired sessions
  global_secondary_index {
    name               = "ExpiresIndex"
    hash_key           = "expires"
    projection_type    = "KEYS_ONLY"
    read_capacity      = var.environment == "prod" ? 5 : 1
    write_capacity     = var.environment == "prod" ? 5 : 1
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
      Purpose     = "session-storage"
    }
  )
}

# Auto-scaling for production
resource "aws_appautoscaling_target" "dynamodb_table_read_target" {
  count              = var.environment == "prod" ? 1 : 0
  max_capacity       = 50
  min_capacity       = 5
  resource_id        = "table/${var.table_name}"
  scalable_dimension = "dynamodb:table:ReadCapacityUnits"
  service_namespace  = "dynamodb"
}

resource "aws_appautoscaling_policy" "dynamodb_table_read_policy" {
  count              = var.environment == "prod" ? 1 : 0
  name               = "DynamoDBReadCapacityUtilization:${aws_appautoscaling_target.dynamodb_table_read_target[0].resource_id}"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.dynamodb_table_read_target[0].resource_id
  scalable_dimension = aws_appautoscaling_target.dynamodb_table_read_target[0].scalable_dimension
  service_namespace  = aws_appautoscaling_target.dynamodb_table_read_target[0].service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "DynamoDBReadCapacityUtilization"
    }

    target_value = 70
  }
}

resource "aws_appautoscaling_target" "dynamodb_table_write_target" {
  count              = var.environment == "prod" ? 1 : 0
  max_capacity       = 50
  min_capacity       = 5
  resource_id        = "table/${var.table_name}"
  scalable_dimension = "dynamodb:table:WriteCapacityUnits"
  service_namespace  = "dynamodb"
}

resource "aws_appautoscaling_policy" "dynamodb_table_write_policy" {
  count              = var.environment == "prod" ? 1 : 0
  name               = "DynamoDBWriteCapacityUtilization:${aws_appautoscaling_target.dynamodb_table_write_target[0].resource_id}"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.dynamodb_table_write_target[0].resource_id
  scalable_dimension = aws_appautoscaling_target.dynamodb_table_write_target[0].scalable_dimension
  service_namespace  = aws_appautoscaling_target.dynamodb_table_write_target[0].service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "DynamoDBWriteCapacityUtilization"
    }

    target_value = 70
  }
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
