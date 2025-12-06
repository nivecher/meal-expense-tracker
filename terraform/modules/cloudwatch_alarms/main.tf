# CloudWatch Alarms Module for Lambda and API Gateway Error Monitoring

# Lambda Error Alarm
resource "aws_cloudwatch_metric_alarm" "lambda_errors" {
  alarm_name          = "${var.app_name}-${var.environment}-lambda-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = 300
  statistic           = "Sum"
  threshold           = var.lambda_error_threshold
  alarm_description   = "This metric monitors lambda function errors"
  treat_missing_data  = "notBreaching"

  dimensions = {
    FunctionName = var.lambda_function_name
  }

  alarm_actions = var.sns_topic_arn != null ? [var.sns_topic_arn] : []

  tags = merge({
    Name        = "${var.app_name}-${var.environment}-lambda-errors-alarm"
    Environment = var.environment
    ManagedBy   = "terraform"
  }, var.tags)
}

# Lambda Throttle Alarm
resource "aws_cloudwatch_metric_alarm" "lambda_throttles" {
  alarm_name          = "${var.app_name}-${var.environment}-lambda-throttles"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "Throttles"
  namespace           = "AWS/Lambda"
  period              = 300
  statistic           = "Sum"
  threshold           = var.lambda_throttle_threshold
  alarm_description   = "This metric monitors lambda function throttles"
  treat_missing_data  = "notBreaching"

  dimensions = {
    FunctionName = var.lambda_function_name
  }

  alarm_actions = var.sns_topic_arn != null ? [var.sns_topic_arn] : []

  tags = merge({
    Name        = "${var.app_name}-${var.environment}-lambda-throttles-alarm"
    Environment = var.environment
    ManagedBy   = "terraform"
  }, var.tags)
}

# Lambda Duration Alarm (High Duration)
resource "aws_cloudwatch_metric_alarm" "lambda_duration" {
  alarm_name          = "${var.app_name}-${var.environment}-lambda-duration"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "Duration"
  namespace           = "AWS/Lambda"
  period              = 300
  statistic           = "Average"
  threshold           = var.lambda_duration_threshold_ms
  alarm_description   = "This metric monitors lambda function duration"
  treat_missing_data  = "notBreaching"

  dimensions = {
    FunctionName = var.lambda_function_name
  }

  alarm_actions = var.sns_topic_arn != null ? [var.sns_topic_arn] : []

  tags = merge({
    Name        = "${var.app_name}-${var.environment}-lambda-duration-alarm"
    Environment = var.environment
    ManagedBy   = "terraform"
  }, var.tags)
}

# Lambda Concurrent Executions Alarm
resource "aws_cloudwatch_metric_alarm" "lambda_concurrent_executions" {
  alarm_name          = "${var.app_name}-${var.environment}-lambda-concurrent"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "ConcurrentExecutions"
  namespace           = "AWS/Lambda"
  period              = 300
  statistic           = "Maximum"
  threshold           = var.lambda_concurrent_threshold
  alarm_description   = "This metric monitors lambda concurrent executions"
  treat_missing_data  = "notBreaching"

  dimensions = {
    FunctionName = var.lambda_function_name
  }

  alarm_actions = var.sns_topic_arn != null ? [var.sns_topic_arn] : []

  tags = merge({
    Name        = "${var.app_name}-${var.environment}-lambda-concurrent-alarm"
    Environment = var.environment
    ManagedBy   = "terraform"
  }, var.tags)
}

# API Gateway 4XX Errors Alarm
resource "aws_cloudwatch_metric_alarm" "api_gateway_4xx_errors" {
  alarm_name          = "${var.app_name}-${var.environment}-api-4xx-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "4XXError"
  namespace           = "AWS/ApiGateway"
  period              = 300
  statistic           = "Sum"
  threshold           = var.api_4xx_error_threshold
  alarm_description   = "This metric monitors API Gateway 4XX errors"
  treat_missing_data  = "notBreaching"

  dimensions = {
    ApiName = var.api_gateway_name
    Stage   = "$default"
  }

  alarm_actions = var.sns_topic_arn != null ? [var.sns_topic_arn] : []

  tags = merge({
    Name        = "${var.app_name}-${var.environment}-api-4xx-errors-alarm"
    Environment = var.environment
    ManagedBy   = "terraform"
  }, var.tags)
}

# API Gateway 5XX Errors Alarm
resource "aws_cloudwatch_metric_alarm" "api_gateway_5xx_errors" {
  alarm_name          = "${var.app_name}-${var.environment}-api-5xx-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "5XXError"
  namespace           = "AWS/ApiGateway"
  period              = 300
  statistic           = "Sum"
  threshold           = var.api_5xx_error_threshold
  alarm_description   = "This metric monitors API Gateway 5XX errors"
  treat_missing_data  = "notBreaching"

  dimensions = {
    ApiName = var.api_gateway_name
    Stage   = "$default"
  }

  alarm_actions = var.sns_topic_arn != null ? [var.sns_topic_arn] : []

  tags = merge({
    Name        = "${var.app_name}-${var.environment}-api-5xx-errors-alarm"
    Environment = var.environment
    ManagedBy   = "terraform"
  }, var.tags)
}

# API Gateway Latency Alarm
resource "aws_cloudwatch_metric_alarm" "api_gateway_latency" {
  alarm_name          = "${var.app_name}-${var.environment}-api-latency"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "Latency"
  namespace           = "AWS/ApiGateway"
  period              = 300
  statistic           = "Average"
  threshold           = var.api_latency_threshold_ms
  alarm_description   = "This metric monitors API Gateway latency"
  treat_missing_data  = "notBreaching"

  dimensions = {
    ApiName = var.api_gateway_name
    Stage   = "$default"
  }

  alarm_actions = var.sns_topic_arn != null ? [var.sns_topic_arn] : []

  tags = merge({
    Name        = "${var.app_name}-${var.environment}-api-latency-alarm"
    Environment = var.environment
    ManagedBy   = "terraform"
  }, var.tags)
}
