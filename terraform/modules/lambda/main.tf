# Lambda function
resource "aws_lambda_function" "main" {
  function_name = "${var.app_name}-${var.environment}"
  role          = var.lambda_role_arn

  # Use the packaged Lambda deployment
  filename         = "${path.module}/../../../dist/app.zip"
  source_code_hash = filebase64sha256("${path.module}/../../../dist/app.zip")

  # Runtime settings - optimized for cost
  runtime     = "python3.13"
  handler     = "wsgi.handler" # Points to the handler function in wsgi.py
  memory_size = var.memory_size
  timeout     = var.timeout

  # Cost optimization: Use ARM architecture (cheaper and often faster for Lambda)
  architectures = ["arm64"]

  # Cost optimization: Enable ephemeral storage for performance without cost
  ephemeral_storage {
    size = 512 # MB - minimum size to avoid performance issues
  }

  # Environment variables with KMS encryption
  environment {
    variables = {
      ENVIRONMENT           = var.environment
      LOG_LEVEL             = var.environment == "prod" ? "INFO" : "DEBUG"
      SECRET_ARN            = var.db_secret_arn
      FLASK_APP             = "app.main"
      FLASK_ENV             = var.environment
      PYTHONPATH            = "/var/task"
      API_GATEWAY_BASE_PATH = "/${var.environment}"
    }
  }

  # Enable KMS encryption for environment variables
  kms_key_arn = var.lambda_kms_key_arn

  # VPC configuration
  vpc_config {
    security_group_ids = var.lambda_security_group_ids
    subnet_ids         = var.subnet_ids
  }

  # Dead Letter Queue (if configured)
  dynamic "dead_letter_config" {
    for_each = var.dead_letter_queue_arn != null ? [1] : []
    content {
      target_arn = var.dead_letter_queue_arn
    }
  }

  # Monitoring and logging
  tracing_config {
    mode = "Active"
  }

  tags = merge({
    Name = "${var.app_name}-${var.environment}-lambda"
  }, var.tags)

  # Ensure the deployment package exists
  depends_on = []
}

# SNS Topic for Dead Letter Queue is now created in the root module

# CloudWatch Log Group for Lambda with KMS encryption
resource "aws_cloudwatch_log_group" "lambda" {
  name              = "/aws/lambda/${aws_lambda_function.main.function_name}"
  retention_in_days = var.environment == "prod" ? 90 : 30
  kms_key_id        = var.logs_kms_key_arn

  tags = merge({
    Name        = "${var.app_name}-${var.environment}-lambda-logs"
    Environment = var.environment
    ManagedBy   = "terraform"
  }, var.tags)
}

# Lambda Permission for API Gateway
resource "aws_lambda_permission" "apigw" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.main.function_name
  principal     = "apigateway.amazonaws.com"

  # The /*/*/* part allows invocation from any stage, method and resource path
  # within API Gateway REST API.
  source_arn = "${var.api_gateway_execution_arn}/*/*"
}
