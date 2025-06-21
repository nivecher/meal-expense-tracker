# IAM role for the Lambda function
resource "aws_iam_role" "secret_rotation_lambda" {
  name = "${var.app_name}-secret-rotation-lambda-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
}

# IAM policy for Secrets Manager access
resource "aws_iam_policy" "secrets_manager_access" {
  name        = "${var.app_name}-secrets-manager-access"
  description = "Policy for accessing Secrets Manager"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:DescribeSecret",
          "secretsmanager:GetSecretValue",
          "secretsmanager:PutSecretValue",
          "secretsmanager:UpdateSecretVersionStage"
        ]
        Resource = [
          var.secret_arn,
          "${var.secret_arn}-*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetRandomPassword",
          "secretsmanager:GetResourcePolicy"
        ]
        Resource = "*"
      }
    ]
  })
}

# IAM policy for CloudWatch Logs and X-Ray
resource "aws_iam_policy" "cloudwatch_logs" {
  name        = "${var.app_name}-monitoring"
  description = "Policy for CloudWatch Logs and X-Ray access"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = [
          "arn:aws:logs:*:*:log-group:/aws/lambda/${var.app_name}-*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "xray:PutTraceSegments",
          "xray:PutTelemetryRecords",
          "xray:GetSamplingRules",
          "xray:GetSamplingTargets",
          "xray:GetSamplingStatisticSummaries"
        ]
        Resource = ["*"]
      },
      {
        Effect = "Allow"
        Action = [
          "kms:Decrypt",
          "kms:GenerateDataKey"
        ]
        Resource = [
          "arn:aws:kms:*:*:key/*"
        ]
      }
    ]
  })
}

# Attach policies to the IAM role
resource "aws_iam_role_policy_attachment" "secrets_manager_access" {
  role       = aws_iam_role.secret_rotation_lambda.name
  policy_arn = aws_iam_policy.secrets_manager_access.arn
}

resource "aws_iam_role_policy_attachment" "cloudwatch_logs" {
  role       = aws_iam_role.secret_rotation_lambda.name
  policy_arn = aws_iam_policy.cloudwatch_logs.arn
}

# VPC configuration for Lambda
resource "aws_iam_role_policy_attachment" "vpc_access" {
  role       = aws_iam_role.secret_rotation_lambda.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"
}

# Lambda function
resource "aws_lambda_function" "secret_rotation" {
  filename      = var.lambda_package_path
  function_name = "${var.app_name}-secret-rotation"
  role          = aws_iam_role.secret_rotation_lambda.arn
  handler       = "secret_rotation.lambda_handler"
  runtime       = var.lambda_runtime
  timeout       = 300 # 5 minutes
  memory_size   = 128

  # Enable X-Ray tracing
  tracing_config {
    mode = "Active"
  }

  vpc_config {
    subnet_ids         = var.subnet_ids
    security_group_ids = [aws_security_group.lambda_sg.id]
  }

  environment {
    variables = {
      MASTER_SECRET_ARN = var.master_secret_arn
    }
  }

  # Ensure the Lambda function is recreated when the package changes
  source_code_hash = filebase64sha256(var.lambda_package_path)
}

# Security group for Lambda function
resource "aws_security_group" "lambda_sg" {
  name        = "${var.app_name}-secret-rotation-sg"
  description = "Security group for secret rotation Lambda function"
  vpc_id      = var.vpc_id

  egress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = [var.vpc_cidr]
    description = "Allow HTTPS outbound to AWS services within VPC"
  }

  tags = {
    Name = "${var.app_name}-secret-rotation-sg"
  }
}

# Allow Lambda to access RDS
resource "aws_security_group_rule" "lambda_to_rds" {
  type                     = "ingress"
  from_port                = 5432
  to_port                  = 5432
  protocol                 = "tcp"
  security_group_id        = var.rds_security_group_id
  source_security_group_id = aws_security_group.lambda_sg.id
  description              = "Allow Lambda to access RDS"
}

# Enable rotation for the secret
resource "aws_secretsmanager_secret_rotation" "rotation" {
  secret_id           = var.secret_arn
  rotation_lambda_arn = aws_lambda_function.secret_rotation.arn

  rotation_rules {
    automatically_after_days = var.rotation_days
  }
}

# Add permission for Secrets Manager to invoke the Lambda function
resource "aws_lambda_permission" "allow_secrets_manager" {
  statement_id  = "AllowExecutionFromSecretsManager"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.secret_rotation.function_name
  principal     = "secretsmanager.amazonaws.com"
  source_arn    = var.secret_arn
}
