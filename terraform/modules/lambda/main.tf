# Lambda module main configuration

data "aws_caller_identity" "current" {}

data "aws_region" "current" {}

data "aws_ssm_parameter" "google_maps_api_key" {
  name = "/${var.app_name}/${var.environment}/google/maps-api-key"
}

# Note: DB_URL will be constructed at runtime in the Lambda function using the secret

# S3 Object for Lambda Layer Package
resource "aws_s3_object" "lambda_layer_package" {
  count = var.layer_s3_bucket != "" && var.layer_s3_key != "" ? 1 : 0

  bucket = var.layer_s3_bucket
  key    = var.layer_s3_key
  source = var.layer_local_path
  etag   = filemd5(var.layer_local_path)

  # Ensure the object is recreated when the source file changes
  lifecycle {
    create_before_destroy = true
  }
}

# S3 Object for Lambda Application Package
resource "aws_s3_object" "lambda_app_package" {
  bucket = var.s3_bucket
  key    = var.s3_key
  source = var.app_local_path
  etag   = filemd5(var.app_local_path)

  # Ensure the object is recreated when the source file changes
  lifecycle {
    create_before_destroy = true
  }
}

# Lambda Layer for Python Dependencies
resource "aws_lambda_layer_version" "python_dependencies" {
  layer_name               = "${var.app_name}-${var.environment}-dependencies"
  description              = "Python dependencies for ${var.app_name} in ${var.environment}"
  s3_bucket                = var.layer_s3_bucket
  s3_key                   = var.layer_s3_key
  s3_object_version        = try(aws_s3_object.lambda_layer_package[0].version_id, null)
  compatible_runtimes      = var.compatible_runtimes
  compatible_architectures = var.compatible_architectures

  # Ensure the layer is recreated when the S3 object changes
  lifecycle {
    create_before_destroy = true

    # Ignore changes to the source code hash as we're using S3 object versioning
    ignore_changes = [
      source_code_hash
    ]
  }

  # Depend on the S3 object to ensure it's created first
  depends_on = [
    aws_s3_object.lambda_layer_package
  ]
}

# CloudWatch Log Group for Lambda
resource "aws_cloudwatch_log_group" "lambda" {
  name              = "/aws/lambda/${var.app_name}-${var.environment}"
  retention_in_days = var.log_retention_in_days
  kms_key_id        = var.kms_key_arn

  tags = merge({
    Name        = "${var.app_name}-${var.environment}-logs"
    Environment = var.environment
    ManagedBy   = "terraform"
  }, var.tags)
}

# SNS Topic for Dead Letter Queue
resource "aws_sns_topic" "lambda_dlq" {
  count = var.create_dlq ? 1 : 0

  name = var.dlq_topic_name != "" ? var.dlq_topic_name : "${var.app_name}-${var.environment}-dlq"

  # Enable server-side encryption using KMS key from root module
  kms_master_key_id = var.kms_key_arn

  tags = merge({
    Name        = var.dlq_topic_name != "" ? var.dlq_topic_name : "${var.app_name}-${var.environment}-dlq"
    Environment = var.environment
    ManagedBy   = "terraform"
  }, var.tags)
}

# SNS Topic Policy for DLQ
resource "aws_sns_topic_policy" "lambda_dlq_policy" {
  count  = var.create_dlq ? 1 : 0
  arn    = aws_sns_topic.lambda_dlq[0].arn
  policy = data.aws_iam_policy_document.sns_topic_policy.json
}

data "aws_iam_policy_document" "sns_topic_policy" {
  statement {
    effect  = "Allow"
    actions = ["SNS:Publish"]

    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }

    resources = [aws_sns_topic.lambda_dlq[0].arn]
  }
}

# IAM Role for Lambda
resource "aws_iam_role" "lambda_role" {
  name = "${var.app_name}-${var.environment}-lambda-role"

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

  tags = merge({
    Name        = "${var.app_name}-${var.environment}-lambda-role"
    Environment = var.environment
    ManagedBy   = "terraform"
  }, var.tags)
}

# IAM Policy for Lambda function
resource "aws_iam_role_policy" "lambda_policy" {
  name = "${var.app_name}-${var.environment}-lambda-policy"
  role = aws_iam_role.lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      # Basic Lambda execution permissions
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:*:*:log-group:/aws/lambda/${var.app_name}-${var.environment}:*"
      },
      # VPC networking permissions
      {
        Effect = "Allow"
        Action = [
          "ec2:CreateNetworkInterface",
          "ec2:DescribeNetworkInterfaces",
          "ec2:DeleteNetworkInterface"
        ]
        Resource = "*"
      },
      # Secrets Manager access
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue"
        ]
        Resource = [
          var.db_secret_arn
        ]
      },

    ]
  })
}

# Attach AWS managed policy for basic Lambda execution
resource "aws_iam_role_policy_attachment" "lambda_basic_execution" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# Attach AWS managed policy for VPC access if VPC is configured
resource "aws_iam_role_policy_attachment" "lambda_vpc_access" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"
}

# Attach the combined IAM policy from the IAM module
resource "aws_iam_role_policy_attachment" "lambda_combined" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = var.lambda_combined_policy_arn
}

# Attach AWS X-Ray managed policy for tracing if enabled
resource "aws_iam_role_policy_attachment" "lambda_xray" {
  count      = var.enable_xray_tracing ? 1 : 0
  role       = aws_iam_role.lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/AWSXRayDaemonWriteAccess"
}

# Get the latest OpenTelemetry Lambda Layer
# ARN format: arn:aws:lambda:${var.aws_region}:901920570463:layer:aws-otel-collector-${var.aws_region}:1

locals {
  otel_layer_arn = "arn:aws:lambda:${var.aws_region}:901920570463:layer:aws-otel-collector-${var.aws_region}:1"

  # Base layers (Python dependencies if configured)
  base_layers = var.layer_s3_bucket != "" && var.layer_s3_key != "" ? [aws_lambda_layer_version.python_dependencies.arn] : []

  # Add OpenTelemetry layer if enabled
  all_layers = var.enable_otel_tracing ? concat(local.base_layers, [local.otel_layer_arn]) : local.base_layers
}

# Lambda Function
resource "aws_lambda_function" "main" {
  function_name = "${var.app_name}-${var.environment}"
  role          = aws_iam_role.lambda_role.arn
  handler       = var.handler
  runtime       = var.runtime
  architectures = var.architectures
  memory_size   = var.memory_size
  timeout       = var.run_migrations ? max(var.timeout, 300) : var.timeout # Min 5 min for migrations
  publish       = true

  # Enable X-Ray tracing
  tracing_config {
    mode = var.enable_xray_tracing ? "Active" : "PassThrough"
  }

  # Use S3 for deployment package
  s3_bucket        = var.s3_bucket
  s3_key           = var.s3_key
  source_code_hash = fileexists(var.app_local_path) ? filebase64sha256(var.app_local_path) : null

  # Attach the required layers
  layers = local.all_layers

  # Environment variables including enhanced monitoring
  environment {
    variables = merge({
      # Database configuration
      DB_SECRET_ARN  = var.db_secret_arn
      RUN_MIGRATIONS = var.run_migrations ? "true" : "false"

      # Google API keys: pass actual values in non-prod, SSM paths in prod
      GOOGLE_MAPS_API_KEY = var.environment != "prod" ? data.aws_ssm_parameter.google_maps_api_key.value : "ssm:${data.aws_ssm_parameter.google_maps_api_key.name}"

      # Database URL: construct in non-prod, use secret in prod
      DATABASE_URL = var.environment != "prod" ? "postgresql+psycopg2://${var.db_username}:${var.db_password}@${var.db_host}:${var.db_port}/${var.db_name}" : null

      # Application configuration
      ENVIRONMENT             = var.environment
      FLASK_ENV               = var.environment == "prod" ? "production" : "development"
      AWS_LAMBDA_EXEC_WRAPPER = var.enable_otel_tracing ? "/opt/otel-instrument" : ""
      LOG_LEVEL               = var.log_level
      ENABLE_AWS_SERVICES     = "true"

      # Note: DB_URL will be constructed at runtime in the Lambda function for prod
    }, var.extra_environment_variables)
  }

  # VPC configuration if VPC ID is provided
  vpc_config {
    subnet_ids         = var.subnet_ids
    security_group_ids = [aws_security_group.lambda.id]
  }

  # Dead Letter Queue configuration if enabled
  dynamic "dead_letter_config" {
    for_each = var.create_dlq ? [1] : []
    content {
      target_arn = aws_sns_topic.lambda_dlq[0].arn
    }
  }

  depends_on = [
    aws_iam_role_policy_attachment.lambda_basic_execution,
    aws_iam_role_policy_attachment.lambda_vpc_access
  ]

  # Tags
  tags = merge(
    {
      Name        = "${var.app_name}-${var.environment}-lambda"
      Environment = var.environment
      ManagedBy   = "Terraform"
    },
    var.tags
  )
}

resource "aws_security_group_rule" "lambda_to_rds" {
  type                     = "egress"
  from_port                = 5432
  to_port                  = 5432
  protocol                 = "tcp"
  security_group_id        = aws_security_group.lambda.id
  source_security_group_id = var.db_security_group_id
  description              = "Allow Lambda to access RDS"
}
