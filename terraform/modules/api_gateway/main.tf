

# Look up the existing Route53 zone if domain_name is provided
data "aws_route53_zone" "main" {
  name         = var.domain_name
  private_zone = false
}

# Look up the existing ACM certificate in us-east-1 if cert_domain is provided
data "aws_acm_certificate" "main" {
  domain   = var.cert_domain
  statuses = ["ISSUED"]

  # We need to use a provider configured for us-east-1 for ACM certificates used by API Gateway
  provider = aws.us-east-1

  lifecycle {
    # Ensure we don't try to create the certificate if it doesn't exist
    postcondition {
      condition     = self.status == "ISSUED"
      error_message = "The ACM certificate for domain ${var.cert_domain} is not in ISSUED state."
    }
  }
}

# API Gateway Custom Domain (only if domain_name and certificate are provided)
resource "aws_apigatewayv2_domain_name" "main" {
  domain_name = var.api_domain_name

  domain_name_configuration {
    certificate_arn = data.aws_acm_certificate.main.arn
    endpoint_type   = "REGIONAL"
    security_policy = "TLS_1_2"
  }

  tags = merge({
    Name        = "${var.app_name}-${var.environment}-domain"
    Environment = var.environment
    ManagedBy   = "terraform"
  }, var.tags)

  lifecycle {
    # Ensure we have a valid domain name configuration
    precondition {
      condition     = can(regex("\\.", var.api_domain_name))
      error_message = "The API domain name '${var.api_domain_name}' is not a valid domain name."
    }

    # Ensure the domain name is within the certificate's scope
    precondition {
      condition = var.cert_domain == null || (var.cert_domain != null && (
        var.api_domain_name == var.cert_domain ||
        endswith(var.api_domain_name, ".${var.cert_domain}") ||
        (startswith(var.cert_domain, "*") && endswith(var.api_domain_name, substr(var.cert_domain, 1, length(var.cert_domain) - 1)))
      ))
      error_message = "The API domain name '${var.api_domain_name}' is not covered by the certificate domain '${var.cert_domain}'."
    }
  }
}

# API Mapping to connect the domain to the API (only if domain and certificate are configured)
resource "aws_apigatewayv2_api_mapping" "main" {
  api_id      = aws_apigatewayv2_api.main.id
  domain_name = aws_apigatewayv2_domain_name.main.id
  stage       = aws_apigatewayv2_stage.main.id # Point to the main stage
}

# Create Route53 record for the API Gateway custom domain (only if domain and certificate are configured)
resource "aws_route53_record" "api" {
  zone_id = data.aws_route53_zone.main.zone_id
  name    = trimsuffix(var.api_domain_name, ".${var.domain_name}")
  type    = "A"

  alias {
    name                   = aws_apigatewayv2_domain_name.main.domain_name_configuration[0].target_domain_name
    zone_id                = aws_apigatewayv2_domain_name.main.domain_name_configuration[0].hosted_zone_id
    evaluate_target_health = false
  }

  allow_overwrite = true

  lifecycle {
    create_before_destroy = true

    # Ensure the domain name is within the Route53 zone
    precondition {
      condition     = endswith(var.api_domain_name, ".${var.domain_name}") || var.api_domain_name == var.domain_name
      error_message = "The API domain name '${var.api_domain_name}' is not within the Route53 zone '${var.domain_name}'."
    }

    # Ensure we have a valid target domain name
    precondition {
      condition     = length(aws_apigatewayv2_domain_name.main.domain_name_configuration) > 0 && aws_apigatewayv2_domain_name.main.domain_name_configuration[0].target_domain_name != ""
      error_message = "The target domain name for the API Gateway custom domain is empty or invalid."
    }
  }
}

# API Gateway HTTP API (HTTP API is cheaper than REST API)
resource "aws_apigatewayv2_api" "main" {
  name          = "${var.app_name}-${var.environment}"
  protocol_type = "HTTP"
  description   = "API Gateway for ${var.app_name} ${var.environment} environment"

  # CORS configuration for Flask Lambda deployment
  cors_configuration {
    # Must specify exact origins when allow_credentials = true
    # Note: API Gateway execution URL will be handled by Lambda CORS headers
    allow_origins = [
      "https://${var.api_domain_name}",                                # Custom domain
      "http://localhost:5000",                                        # Local dev
      "http://127.0.0.1:5000"                                        # Local dev
    ]

    # HTTP methods for Flask application
    allow_methods = [
      "GET",
      "POST",
      "OPTIONS",
      "PUT",
      "PATCH",
      "DELETE",
    ]

    # Headers needed for Flask forms and sessions (CSRF disabled for Lambda)
    allow_headers = [
      "Content-Type",
      "Authorization",
      "X-Requested-With",
      "Accept",
      "Origin",
      "Cache-Control"
    ]

    # Headers to expose to JavaScript
    expose_headers = [
      "Content-Length",
      "Content-Type"
    ]

    # REQUIRED for Flask sessions/cookies to work (even with DynamoDB)
    allow_credentials = true

    # Cache preflight requests for 1 hour
    max_age = 3600
  }

  tags = merge({
    Name        = "${var.app_name}-${var.environment}-api"
    Environment = var.environment
    ManagedBy   = "terraform"
  }, var.tags)
}

# API Gateway Stage
resource "aws_apigatewayv2_stage" "main" {
  api_id      = aws_apigatewayv2_api.main.id
  name        = "$default"
  auto_deploy = true

  # Access logging settings
  access_log_settings {
    destination_arn = aws_cloudwatch_log_group.api_gw.arn
    format = jsonencode({
      requestId        = "$context.requestId"
      ip               = "$context.identity.sourceIp"
      requestTime      = "$context.requestTime"
      httpMethod       = "$context.httpMethod"
      routeKey         = "$context.routeKey"
      status           = "$context.status"
      protocol         = "$context.protocol"
      responseLength   = "$context.responseLength"
      integrationError = "$context.integrationErrorMessage"
    })
  }

  default_route_settings {
    detailed_metrics_enabled = true
    throttling_burst_limit   = 1000
    throttling_rate_limit    = 500
  }

  tags = merge({
    Name        = "${var.app_name}-${var.environment}-stage"
    Environment = var.environment
    ManagedBy   = "terraform"
  }, var.tags)
}

# CloudWatch Log Group for API Gateway
resource "aws_cloudwatch_log_group" "api_gw" {
  name              = "/aws/api-gateway/${var.app_name}-${var.environment}"
  retention_in_days = 7
  kms_key_id        = var.logs_kms_key_arn

  tags = merge({
    Name        = "${var.app_name}-${var.environment}-api-gw-logs"
    Environment = var.environment
    ManagedBy   = "terraform"
  }, var.tags)
}

# API Gateway Lambda Integration
resource "aws_apigatewayv2_integration" "lambda" {
  # Always create the integration, but only configure it if lambda_invoke_arn is provided
  api_id             = aws_apigatewayv2_api.main.id
  integration_type   = var.lambda_invoke_arn != null ? "AWS_PROXY" : "HTTP_PROXY"
  integration_method = var.lambda_invoke_arn != null ? "POST" : "ANY"
  integration_uri    = var.lambda_invoke_arn != null ? var.lambda_invoke_arn : "http://example.com"

  # Only set the payload format version for Lambda integrations
  payload_format_version = var.lambda_invoke_arn != null ? "2.0" : null

  # Only set connection type for Lambda integrations
  connection_type = var.lambda_invoke_arn != null ? "INTERNET" : null

  lifecycle {
    # Ignore changes to integration_uri as it may be updated later by the Lambda module
    ignore_changes = [integration_uri]

    # Ensure the integration is created before any routes that depend on it
    create_before_destroy = true
  }

  # Explicitly depend on the API to ensure it exists
  depends_on = [aws_apigatewayv2_api.main]
}

# Allow API Gateway to invoke the Lambda function
resource "aws_lambda_permission" "api_gateway" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = var.lambda_function_name
  principal     = "apigateway.amazonaws.com"

  # The /*/* part allows invocation from any stage and method
  # within the API Gateway HTTP API
  source_arn = "${aws_apigatewayv2_api.main.execution_arn}/*/*"

  # Ensure the API Gateway exists before creating the permission
  depends_on = [aws_apigatewayv2_api.main]
}

# Add a catch-all {proxy+} route
resource "aws_apigatewayv2_route" "proxy" {
  # Always create the route, but only set the target if lambda_invoke_arn is provided
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "ANY /{proxy+}"

  # Set target to integration ID if lambda_invoke_arn is provided, otherwise null
  target = "integrations/${aws_apigatewayv2_integration.lambda.id}"

  # Depend on the integration being created first
  depends_on = [aws_apigatewayv2_integration.lambda]

  lifecycle {
    # Ensure the route is destroyed before the integration is recreated
    create_before_destroy = false
  }
}

# Add a root route
resource "aws_apigatewayv2_route" "root" {
  # Always create the route, but only set the target if lambda_invoke_arn is provided
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "ANY /"

  # Set target to integration ID if lambda_invoke_arn is provided, otherwise null
  target = var.lambda_invoke_arn != null ? "integrations/${aws_apigatewayv2_integration.lambda.id}" : null

  # Depend on the integration being created first
  depends_on = [aws_apigatewayv2_integration.lambda]

  lifecycle {
    # Ensure the route is destroyed before the integration is recreated
    create_before_destroy = false
  }
}

# Note: Route responses are not supported for HTTP API with proxy integration
# The API will automatically handle responses from the Lambda function
