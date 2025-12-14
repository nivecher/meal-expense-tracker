# Lambda module main configuration

data "aws_caller_identity" "current" {}

data "aws_region" "current" {}

data "aws_ssm_parameter" "google_maps_api_key" {
  name = "/${var.app_name}/${var.environment}/google/maps/api-key"
}

data "aws_ssm_parameter" "google_maps_map_id" {
  name = "/${var.app_name}/${var.environment}/google/maps/map-id"
}

# Get the application secret key from SSM Parameter Store using the provided ARN
data "aws_ssm_parameter" "app_secret_key" {
  name = "/${var.app_name}/${var.environment}/app/secret_key"

  # Ensure the parameter exists before trying to access it
  # This will cause Terraform to fail early if the parameter doesn't exist
  depends_on = [
    var.app_secret_key_arn
  ]
}

# Get ECR repository for container images
data "aws_ecr_repository" "lambda" {
  name = "${var.app_name}-${var.environment}-lambda"
}

# Note: DB_URL will be constructed at runtime in the Lambda function using the secret

# No S3 objects needed for container images - everything is in the container

# No Lambda layers needed for container images - dependencies are in the container

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
      # Secrets Manager access for Supabase
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue",
          "secretsmanager:DescribeSecret"
        ]
        Resource = [
          "arn:aws:secretsmanager:${data.aws_region.current.id}:${data.aws_caller_identity.current.account_id}:secret:${var.app_name}/${var.environment}/supabase-*",
          "arn:aws:secretsmanager:${data.aws_region.current.id}:${data.aws_caller_identity.current.account_id}:secret:${var.app_name}*supabase*"
        ]
      },
      # SSM Parameter Store access for application configuration
      {
        Effect = "Allow"
        Action = [
          "ssm:GetParameter",
          "ssm:GetParameters",
          "ssm:GetParametersByPath"
        ]
        Resource = [
          "arn:aws:ssm:${data.aws_region.current.id}:${data.aws_caller_identity.current.account_id}:parameter/${var.app_name}/${var.environment}/*"
        ]
      },
      # KMS decryption for SSM parameters
      {
        Effect = "Allow"
        Action = [
          "kms:Decrypt",
          "kms:DescribeKey"
        ]
        Resource = [
          "arn:aws:kms:${data.aws_region.current.id}:${data.aws_caller_identity.current.account_id}:key/*"
        ],
        Condition = {
          StringLike = {
            "kms:RequestAlias" = "alias/aws/ssm"
          }
        }
      },

    ]
  })
}

# Attach AWS managed policy for basic Lambda execution
resource "aws_iam_role_policy_attachment" "lambda_basic_execution" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# VPC policy attachment removed - not using VPC anymore

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


# Lambda Function
resource "aws_lambda_function" "main" {
  function_name = "${var.app_name}-${var.environment}"
  role          = aws_iam_role.lambda_role.arn
  architectures = var.architectures
  memory_size   = var.memory_size
  timeout       = var.run_migrations ? max(var.timeout, 300) : var.timeout # Min 5 min for migrations
  publish       = true

  # Package type - determines deployment method
  package_type = var.package_type

  # Handler and runtime only needed for ZIP packages
  # For container images, handler is specified in Dockerfile CMD, not here
  handler = var.package_type == "Zip" ? var.handler : null
  runtime = var.package_type == "Zip" ? var.runtime : null

  # Container image URI for Image packages - use latest tag for easier iteration
  # Note: Must ensure the image is tagged as 'latest' when pushing to ECR
  image_uri = var.package_type == "Image" ? "${data.aws_ecr_repository.lambda.repository_url}:latest" : null

  # S3 configuration for ZIP packages (only if package_type is Zip)
  s3_bucket = var.package_type == "Zip" ? var.s3_bucket : null
  s3_key    = var.package_type == "Zip" ? var.s3_key : null

  # Ensure IAM roles are attached before Lambda deployment
  depends_on = [
    aws_iam_role_policy_attachment.lambda_basic_execution,
    aws_iam_role_policy_attachment.lambda_combined,
  ]

  # Enable X-Ray tracing
  tracing_config {
    mode = var.enable_xray_tracing ? "Active" : "PassThrough"
  }

  # Container image URI for Image package type (not used for ZIP packages)
  # image_uri = var.package_type == "Image" ? "${data.aws_ecr_repository.lambda.repository_url}:latest" : null

  # Source code hash for Zip packages (not needed for container images)
  source_code_hash = var.package_type == "Zip" ? null : null

  # Lifecycle rules to prevent unnecessary updates
  lifecycle {
    # Ignore source_code_hash changes for all package types
    # This prevents unnecessary updates when only metadata changes
    ignore_changes = [
      source_code_hash,
    ]
  }

  # Environment variables including enhanced monitoring
  environment {
    variables = merge(
      {
        # Standard environment variables
        ENVIRONMENT = var.environment
        APP_NAME    = var.app_name
        LOG_LEVEL   = var.log_level

        # Application secret key from SSM Parameter Store
        SECRET_KEY = data.aws_ssm_parameter.app_secret_key.value

        # Google Maps configuration
        GOOGLE_MAPS_API_KEY = data.aws_ssm_parameter.google_maps_api_key.value
        GOOGLE_MAPS_MAP_ID  = data.aws_ssm_parameter.google_maps_map_id.value

        # Notification configuration (AWS SNS)
        NOTIFICATIONS_ENABLED = "true"
        # SNS_TOPIC_ARN will be constructed at runtime in config.py

        # Database configuration will be set at runtime via the secret

        # CORS configuration
        CORS_ORIGINS        = var.environment == "prod" ? "https://${var.server_name}" : "*"
        CORS_METHODS        = "GET,POST,PUT,DELETE,OPTIONS,HEAD"
        CORS_HEADERS        = "Content-Type,Authorization,X-CSRF-Token,X-Requested-With"
        CORS_EXPOSE_HEADERS = "Content-Length,X-CSRF-Token"
        CORS_MAX_AGE        = "600" # 10 minutes

        # Application configuration
        FLASK_ENV           = "production"
        ENABLE_AWS_SERVICES = "true"
        # DATABASE_URL not set - Lambda will read from Secrets Manager directly
        DATABASE_SECRET_NAME = "meal-expense-tracker/${var.environment}/supabase-connection"

        # Security configuration - include both custom domain and API Gateway execution URL
        ALLOWED_REFERRER_DOMAINS = "${var.server_name},${var.api_gateway_domain_name}"
        SERVER_NAME              = var.server_name
        API_GATEWAY_DOMAIN_NAME  = var.api_gateway_domain_name

        SESSION_TIMEOUT = "3600" # 1 hour session timeout

        # X-Ray tracing is enabled via IAM permissions and X-Ray daemon
        # _X_AMZN_TRACE_ID is automatically set by Lambda when X-Ray tracing is enabled

        # OpenTelemetry configuration
        OPENTELEMETRY_COLLECTOR_CONFIG_FILE = var.enable_otel_tracing ? "/var/task/opentelemetry-collector-config.yaml" : ""
        AWS_LAMBDA_EXEC_WRAPPER             = var.enable_otel_tracing ? "/opt/otel-handler" : ""

        # Set Python path to include the layer
        PYTHONPATH = "/opt/python:/opt/python/lib/python3.13/site-packages"

        # Database migration configuration
        AUTO_MIGRATE = var.run_migrations ? "true" : "false"

        # Note: DB_URL will be constructed at runtime in the Lambda function for prod
      },
      var.extra_environment_variables
    )
  }

  # VPC configuration only if subnet IDs are provided (optional for Lambda without VPC)
  dynamic "vpc_config" {
    for_each = length(var.subnet_ids) > 0 ? [1] : []
    content {
      subnet_ids         = var.subnet_ids
      security_group_ids = var.vpc_id != "" ? [aws_security_group.lambda[0].id] : []
    }
  }

  # Dead Letter Queue configuration if enabled
  dynamic "dead_letter_config" {
    for_each = var.create_dlq ? [1] : []
    content {
      target_arn = aws_sns_topic.lambda_dlq[0].arn
    }
  }

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
