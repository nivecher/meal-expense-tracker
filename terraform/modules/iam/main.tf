# Note: Lambda IAM role has been moved to the Lambda module for better encapsulation
# and to follow the principle of single responsibility.

# Combined IAM Policy that can be attached to the Lambda role
resource "aws_iam_policy" "lambda_combined" {
  name        = "${var.app_name}-${var.environment}-lambda-combined-policy"
  description = "Combined IAM policy for Lambda function"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      # Secrets Manager access
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue",
          "secretsmanager:DescribeSecret"
        ]
        Resource = [
          var.db_secret_arn
        ]
      },
      # RDS Database Access
      {
        Effect = "Allow"
        Action = [
          "rds-db:connect",
          "rds-db:executeStatement",
          "rds-db:select"
        ]
        Resource = [
          "arn:aws:rds-db:${var.region}:${var.account_id}:dbuser:${var.db_instance_identifier}/${var.db_username}"
        ]
      },
      # RDS Management
      {
        Effect = "Allow"
        Action = [
          "rds:DescribeDBInstances",
          "rds:DescribeDBClusters"
        ]
        Resource = "*"
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
      # VPC Networking
      {
        Effect = "Allow"
        Action = [
          "ec2:CreateNetworkInterface",
          "ec2:DescribeNetworkInterfaces",
          "ec2:DeleteNetworkInterface",
          "ec2:AssignPrivateIpAddresses",
          "ec2:UnassignPrivateIpAddresses"
        ]
        Resource = ["*"]
      },
      # SNS Publish for Dead Letter Queue
      {
        Effect = "Allow"
        Action = [
          "sns:Publish"
        ]
        Resource = [
          "*" # Temporarily using wildcard to test, will scope down after verification
        ]
      },
      # KMS Decrypt for Secrets Manager
      {
        Effect = "Allow"
        Action = [
          "kms:Decrypt",
          "kms:DescribeKey"
        ]
        Resource = [
          "*" # This should be scoped to the specific KMS key ARN when known
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
