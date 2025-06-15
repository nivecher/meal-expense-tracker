# Look up the existing Route53 zone if domain_name is provided
data "aws_route53_zone" "main" {
  count        = var.domain_name != null && var.create_route53_records ? 1 : 0
  name         = var.domain_name
  private_zone = false
}

# Look up the existing ACM certificate in us-east-1 if domain_name is provided
data "aws_acm_certificate" "main" {
  count    = var.domain_name != null ? 1 : 0
  domain   = "*.${var.domain_name}" # Assuming wildcard cert exists
  statuses = ["ISSUED"]
  provider = aws.us-east-1 # ACM certificates for API Gateway must be in us-east-1
}

# API Gateway Custom Domain (optional, only if domain_name is provided)
resource "aws_apigatewayv2_domain_name" "main" {
  count       = var.domain_name != null ? 1 : 0
  domain_name = var.api_domain_name

  domain_name_configuration {
    certificate_arn = data.aws_acm_certificate.main[0].arn
    endpoint_type   = "REGIONAL"
    security_policy = "TLS_1_2"
  }

  tags = merge({
    Name        = "${var.app_name}-${var.environment}-domain"
    Environment = var.environment
    ManagedBy   = "terraform"
  }, var.tags)
}

# API Mapping to connect the domain to the API (only if domain is configured)
resource "aws_apigatewayv2_api_mapping" "main" {
  count       = var.domain_name != null ? 1 : 0
  api_id      = aws_apigatewayv2_api.main.id
  domain_name = aws_apigatewayv2_domain_name.main[0].id
  stage       = aws_apigatewayv2_stage.main.id # Point to the main stage
}

# Create Route53 record for the API Gateway custom domain (only if domain is configured and create_route53_records is true)
resource "aws_route53_record" "api" {
  count   = var.domain_name != null && var.create_route53_records ? 1 : 0
  zone_id = data.aws_route53_zone.main[0].zone_id
  name    = trimsuffix(var.api_domain_name, ".${var.domain_name}")
  type    = "A"

  alias {
    name                   = one(aws_apigatewayv2_domain_name.main[*].domain_name_configuration[0].target_domain_name)
    zone_id                = one(aws_apigatewayv2_domain_name.main[*].domain_name_configuration[0].hosted_zone_id)
    evaluate_target_health = false
  }
}

# API Gateway HTTP API (HTTP API is cheaper than REST API)
resource "aws_apigatewayv2_api" "main" {
  name          = "${var.app_name}-${var.environment}"
  protocol_type = "HTTP"

  # CORS configuration
  cors_configuration {
    allow_credentials = false
    allow_headers     = ["Content-Type", "X-Amz-Date", "Authorization", "X-Api-Key"]
    allow_methods     = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    allow_origins     = var.environment == "dev" ? ["*"] : ["https://${var.domain_name}"]
    expose_headers    = ["Content-Length"]
    max_age           = 3600
  }

  tags = merge({
    Name        = "${var.app_name}-${var.environment}-api"
    Environment = var.environment
    ManagedBy   = "terraform"
  }, var.tags)
}

# API Gateway Lambda Integration
resource "aws_apigatewayv2_integration" "lambda" {
  api_id             = aws_apigatewayv2_api.main.id
  integration_type   = "AWS_PROXY"
  integration_method = "POST"
  integration_uri    = var.lambda_invoke_arn
}

# API Gateway Route - Catch-all route
resource "aws_apigatewayv2_route" "proxy" {
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "$default" # Using $default as it's less likely to conflict
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"

  # Add lifecycle to ignore changes to the route key to prevent conflicts
  lifecycle {
    ignore_changes = [route_key]
  }
}

# API Gateway Stage
resource "aws_apigatewayv2_stage" "main" {
  api_id      = aws_apigatewayv2_api.main.id
  name        = var.environment
  auto_deploy = true # Auto-deploy changes to this stage

  # Access logging configuration
  access_log_settings {
    destination_arn = aws_cloudwatch_log_group.api_gw.arn
    format = jsonencode({
      requestId          = "$context.requestId"
      ip                 = "$context.identity.sourceIp"
      caller             = "$context.identity.caller"
      user               = "$context.identity.user"
      requestTime        = "$context.requestTime"
      httpMethod         = "$context.httpMethod"
      resourcePath       = "$context.resourcePath"
      status             = "$context.status"
      protocol           = "$context.protocol"
      responseLength     = "$context.responseLength"
      integrationLatency = "$context.integrationLatency"
      integrationStatus  = "$context.integrationStatus"
      responseLatency    = "$context.responseLatency"
    })
  }

  # Default route settings
  default_route_settings {
    detailed_metrics_enabled = var.environment == "prod"
    data_trace_enabled       = false
    logging_level            = "ERROR"
    throttling_burst_limit   = var.environment == "prod" ? 100 : 10
    throttling_rate_limit    = var.environment == "prod" ? 50 : 5
  }

  tags = merge({
    Name        = "${var.app_name}-${var.environment}-stage"
    Environment = var.environment
    ManagedBy   = "terraform"
  }, var.tags)
}

# CloudWatch Log Group for API Gateway
resource "aws_cloudwatch_log_group" "api_gw" {
  name              = "/aws/apigateway/${var.app_name}-${var.environment}"
  retention_in_days = var.environment == "prod" ? 90 : 30
  kms_key_id        = var.logs_kms_key_arn

  tags = merge({
    Name        = "${var.app_name}-${var.environment}-api-logs"
    Environment = var.environment
    ManagedBy   = "terraform"
  }, var.tags)
}

# Lambda Permission to allow API Gateway to invoke the function
resource "aws_lambda_permission" "api_gateway" {
  # Use a fixed statement ID with a random suffix to avoid conflicts
  statement_id  = "AllowAPIGatewayInvoke-${substr(sha256("${var.app_name}-${var.environment}"), 0, 16)}"
  action        = "lambda:InvokeFunction"
  function_name = var.lambda_function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.main.execution_arn}/*/*"

  # Ensure the API Gateway is created before the permission
  depends_on = [aws_apigatewayv2_api.main]

  # Use a lifecycle to ignore changes to the statement_id
  lifecycle {
    ignore_changes = [statement_id]
  }
}
