# Note: Lambda IAM role has been moved to the Lambda module for better encapsulation
# and to follow the principle of single responsibility.

# Combined IAM Policy that can be attached to the Lambda role
resource "aws_iam_policy" "lambda_combined" {
  name        = "${var.app_name}-${var.environment}-lambda-combined-policy"
  description = "Combined IAM policy for Lambda function"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      # Secrets Manager access for Supabase
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue",
          "secretsmanager:DescribeSecret"
        ]
        Resource = [
          "arn:aws:secretsmanager:${var.region}:${var.account_id}:secret:${var.app_name}/${var.environment}/supabase-*"
        ]
      },
      # CloudWatch Logs
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = [
          "arn:aws:logs:*:*:*"
        ]
      },
      # SNS access for notifications and dead letter queues
      {
        Effect = "Allow"
        Action = [
          "sns:Publish",
          "sns:GetTopicAttributes",
          "sns:ListTopics",
          "sns:GetSubscriptionAttributes"
        ]
        Resource = [
          "*" # Temporarily using wildcard to test, will scope down after verification
        ]
      },
      # KMS access for Secrets Manager and S3 encryption
      {
        Effect = "Allow"
        Action = [
          "kms:Decrypt",
          "kms:DescribeKey",
          "kms:GenerateDataKey"
        ]
        Resource = [
          "*" # This should be scoped to specific KMS key ARNs when known
        ]
      },
      # SSM Parameter Store access for Google API keys
      {
        Effect = "Allow"
        Action = [
          "ssm:GetParameter",
          "ssm:GetParameters",
          "ssm:GetParametersByPath"
        ]
        Resource = [
          "arn:aws:ssm:${var.region}:${var.account_id}:parameter/${var.app_name}/${var.environment}/google/*"
        ]
      },
      # AWS SES access for email functionality
      {
        Effect = "Allow"
        Action = [
          "ses:SendEmail",
          "ses:SendRawEmail"
        ]
        Resource = "*"
      },
      # S3 access for receipt storage
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject",
          "s3:ListBucket"
        ]
        Resource = [
          "arn:aws:s3:::${var.app_name}-${var.environment}-receipts",
          "arn:aws:s3:::${var.app_name}-${var.environment}-receipts/*"
        ]
      }
    ]
  })
}

# Note: Policy attachments have been moved to the Lambda module
# where the IAM role is now managed. The policy is still created here
# and can be attached by the calling module as needed.

# Output the policy ARN so it can be attached by the Lambda module
output "lambda_combined_policy_arn" {
  description = "The ARN of the combined IAM policy for Lambda functions"
  value       = aws_iam_policy.lambda_combined.arn
}
