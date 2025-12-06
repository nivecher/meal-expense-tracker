# CloudWatch Dashboard Module for Lambda and API Gateway Monitoring

resource "aws_cloudwatch_dashboard" "main" {
  dashboard_name = "${var.app_name}-${var.environment}-debug-dashboard"

  dashboard_body = jsonencode({
    widgets = concat(
      # Lambda Function Metrics
      [
        {
          type   = "metric"
          x      = 0
          y      = 0
          width  = 12
          height = 6
          properties = {
            metrics = [
              ["AWS/Lambda", "Invocations", "FunctionName", var.lambda_function_name],
              [".", "Errors", "FunctionName", var.lambda_function_name],
              [".", "Throttles", "FunctionName", var.lambda_function_name]
            ]
            stat    = "Sum"
            view    = "timeSeries"
            stacked = false
            region  = var.aws_region
            title   = "Lambda Invocations, Errors, Throttles"
            period  = 300
          }
        },
        {
          type   = "metric"
          x      = 12
          y      = 0
          width  = 12
          height = 6
          properties = {
            metrics = [
              ["AWS/Lambda", "Duration", "FunctionName", var.lambda_function_name],
              [".", "Duration", "FunctionName", var.lambda_function_name]
            ]
            stat    = "Average"
            view    = "timeSeries"
            stacked = false
            region  = var.aws_region
            title   = "Lambda Duration (Avg & Max)"
            period  = 300
          }
        },
        {
          type   = "metric"
          x      = 0
          y      = 6
          width  = 12
          height = 6
          properties = {
            metrics = [
              ["AWS/Lambda", "ConcurrentExecutions", "FunctionName", var.lambda_function_name]
            ]
            stat    = "Maximum"
            view    = "timeSeries"
            stacked = false
            region  = var.aws_region
            title   = "Lambda Concurrent Executions"
            period  = 300
          }
        },
        {
          type   = "metric"
          x      = 12
          y      = 6
          width  = 12
          height = 6
          properties = {
            metrics = [
              ["AWS/Lambda", "Duration", "FunctionName", var.lambda_function_name],
              [".", "Duration", "FunctionName", var.lambda_function_name],
              [".", "Duration", "FunctionName", var.lambda_function_name]
            ]
            stat    = "p99"
            view    = "timeSeries"
            stacked = false
            region  = var.aws_region
            title   = "Lambda Duration Percentiles"
            period  = 300
          }
        },
        {
          type   = "metric"
          x      = 0
          y      = 12
          width  = 12
          height = 6
          properties = {
            metrics = [
              ["AWS/Lambda", "Errors", "FunctionName", var.lambda_function_name],
              [".", "Invocations", "FunctionName", var.lambda_function_name]
            ]
            stat    = "Sum"
            view    = "timeSeries"
            stacked = false
            region  = var.aws_region
            title   = "Lambda Error Rate"
            period  = 300
            annotations = {
              horizontal = [
                {
                  value   = 0
                  label   = "Zero Errors"
                  color   = "#2ca02c"
                  fill    = "below"
                  visible = true
                  yAxis   = "left"
                }
              ]
            }
          }
        }
      ],
      # API Gateway Metrics
      [
        {
          type   = "metric"
          x      = 12
          y      = 12
          width  = 12
          height = 6
          properties = {
            metrics = [
              ["AWS/ApiGateway", "Count", "ApiName", "${var.app_name}-${var.environment}", "Stage", "$default"],
              [".", "4XXError", "ApiName", "${var.app_name}-${var.environment}", "Stage", "$default"],
              [".", "5XXError", "ApiName", "${var.app_name}-${var.environment}", "Stage", "$default"]
            ]
            stat    = "Sum"
            view    = "timeSeries"
            stacked = false
            region  = var.aws_region
            title   = "API Gateway Request Count & Errors"
            period  = 300
          }
        },
        {
          type   = "metric"
          x      = 0
          y      = 18
          width  = 12
          height = 6
          properties = {
            metrics = [
              ["AWS/ApiGateway", "Latency", "ApiName", "${var.app_name}-${var.environment}", "Stage", "$default"]
            ]
            stat    = "Average"
            view    = "timeSeries"
            stacked = false
            region  = var.aws_region
            title   = "API Gateway Average Latency"
            period  = 300
          }
        },
        {
          type   = "metric"
          x      = 12
          y      = 18
          width  = 12
          height = 6
          properties = {
            metrics = [
              ["AWS/ApiGateway", "Latency", "ApiName", "${var.app_name}-${var.environment}", "Stage", "$default"],
              [".", "Latency", "ApiName", "${var.app_name}-${var.environment}", "Stage", "$default"],
              [".", "Latency", "ApiName", "${var.app_name}-${var.environment}", "Stage", "$default"]
            ]
            stat    = "p99"
            view    = "timeSeries"
            stacked = false
            region  = var.aws_region
            title   = "API Gateway Latency Percentiles"
            period  = 300
          }
        },
        {
          type   = "metric"
          x      = 0
          y      = 24
          width  = 12
          height = 6
          properties = {
            metrics = [
              ["AWS/ApiGateway", "4XXError", "ApiName", "${var.app_name}-${var.environment}", "Stage", "$default"],
              [".", "5XXError", "ApiName", "${var.app_name}-${var.environment}", "Stage", "$default"]
            ]
            stat    = "Sum"
            view    = "timeSeries"
            stacked = false
            region  = var.aws_region
            title   = "API Gateway Error Breakdown"
            period  = 300
            annotations = {
              horizontal = [
                {
                  value   = 0
                  label   = "Zero Errors"
                  color   = "#2ca02c"
                  fill    = "below"
                  visible = true
                  yAxis   = "left"
                }
              ]
            }
          }
        },
        {
          type   = "metric"
          x      = 12
          y      = 24
          width  = 12
          height = 6
          properties = {
            metrics = [
              ["AWS/ApiGateway", "IntegrationLatency", "ApiName", "${var.app_name}-${var.environment}", "Stage", "$default"],
              [".", "Latency", "ApiName", "${var.app_name}-${var.environment}", "Stage", "$default"]
            ]
            stat    = "Average"
            view    = "timeSeries"
            stacked = false
            region  = var.aws_region
            title   = "API Gateway vs Integration Latency"
            period  = 300
          }
        }
      ],
      # CloudWatch Logs Insights
      [
        {
          type   = "log"
          x      = 0
          y      = 30
          width  = 24
          height = 6
          properties = {
            query   = "SOURCE '${var.lambda_log_group_name}'\n| fields @timestamp, @message\n| filter @message like /ERROR/ or @message like /Exception/ or @message like /Traceback/\n| sort @timestamp desc\n| limit 100"
            region  = var.aws_region
            title   = "Recent Lambda Errors (Last 100)"
            stacked = false
          }
        },
        {
          type   = "log"
          x      = 0
          y      = 36
          width  = 24
          height = 6
          properties = {
            query   = "SOURCE '${var.api_gateway_log_group_name}'\n| fields @timestamp, @message\n| filter @message like /error/ or status >= 400\n| sort @timestamp desc\n| limit 100"
            region  = var.aws_region
            title   = "Recent API Gateway Errors (Last 100)"
            stacked = false
          }
        },
        {
          type   = "log"
          x      = 0
          y      = 42
          width  = 24
          height = 6
          properties = {
            query   = "SOURCE '${var.lambda_log_group_name}'\n| fields @timestamp, @message, @requestId\n| filter @message like /ERROR/\n| stats count() by @requestId\n| sort count desc\n| limit 20"
            region  = var.aws_region
            title   = "Top Error Request IDs"
            stacked = false
          }
        }
      ]
    )
  })

  # Note: aws_cloudwatch_dashboard resource does not support tags
}
