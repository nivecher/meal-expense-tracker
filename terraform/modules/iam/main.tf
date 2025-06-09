# IAM Role for Lambda
resource "aws_iam_role" "lambda_exec" {
  name = "${var.app_name}-${var.environment}-lambda-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = ["lambda.amazonaws.com"]
      }
    }]
  })

  tags = var.tags
}

# Basic Lambda execution policy attachment
resource "aws_iam_role_policy_attachment" "lambda_basic" {
  role       = aws_iam_role.lambda_exec.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# Combined IAM Policy for Lambda
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
      # RDS access
      {
        Effect = "Allow"
        Action = [
          "rds:Connect",
          "rds-db:connect"
        ]
        Resource = [
          "arn:aws:rds:${var.region}:${var.account_id}:db:${var.db_identifier}",
          "arn:aws:rds:${var.region}:${var.account_id}:cluster:${var.db_identifier}"
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
      }
    ]
  })
}

# Attach the combined policy to the Lambda role
resource "aws_iam_role_policy_attachment" "lambda_combined" {
  role       = aws_iam_role.lambda_exec.name
  policy_arn = aws_iam_policy.lambda_combined.arn
}
