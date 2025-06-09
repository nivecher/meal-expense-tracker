# Lambda function
resource "aws_lambda_function" "main" {
  function_name = "${var.app_name}-${var.environment}"
  role          = var.lambda_role_arn

  # Use the packaged Lambda deployment
  filename         = "${path.module}/../../app.zip"
  source_code_hash = filebase64sha256("${path.module}/../../app.zip")

  # Runtime settings
  runtime     = "python3.11"
  handler     = "app.main.lambda_handler"
  memory_size = var.memory_size
  timeout     = var.timeout

  # Environment variables
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

  # VPC configuration
  vpc_config {
    security_group_ids = var.lambda_security_group_ids
    subnet_ids         = var.subnet_ids
  }

  # Dead Letter Queue
  dead_letter_config {
    target_arn = aws_sns_topic.lambda_dlq.arn
  }

  # Monitoring and logging
  tracing_config {
    mode = "Active"
  }

  tags = merge({
    Name = "${var.app_name}-${var.environment}-lambda"
  }, var.tags)

  # Ensure the deployment package exists
  depends_on = [
    aws_sns_topic.lambda_dlq,
    aws_sns_topic_policy.lambda_dlq_policy
  ]
}

# SNS Topic for Dead Letter Queue
resource "aws_sns_topic" "lambda_dlq" {
  name = "${var.app_name}-${var.environment}-lambda-dlq"

  tags = merge({
    Name = "${var.app_name}-${var.environment}-lambda-dlq"
  }, var.tags)
}

# Allow Lambda service to publish to the DLQ
resource "aws_sns_topic_policy" "lambda_dlq_policy" {
  arn    = aws_sns_topic.lambda_dlq.arn
  policy = data.aws_iam_policy_document.lambda_dlq_policy.json
}

data "aws_iam_policy_document" "lambda_dlq_policy" {
  statement {
    effect  = "Allow"
    actions = ["SNS:Publish"]

    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }

    resources = [aws_sns_topic.lambda_dlq.arn]
  }
}

# CloudWatch Log Group for Lambda
resource "aws_cloudwatch_log_group" "lambda" {
  name              = "/aws/lambda/${aws_lambda_function.main.function_name}"
  retention_in_days = var.environment == "prod" ? 90 : 30

  tags = merge({
    Name = "${var.app_name}-${var.environment}-lambda-logs"
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
