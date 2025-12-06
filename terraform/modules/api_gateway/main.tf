

# Look up the existing Route53 zone if domain_name is provided
data "aws_route53_zone" "main" {
  name         = var.domain_name
  private_zone = false
}

# Look up the existing ACM certificate in us-east-1 if cert_domain is provided
data "aws_acm_certificate" "main" {
  domain      = var.cert_domain
  statuses    = ["ISSUED"]
  key_types   = ["RSA_2048"]
  types       = ["AMAZON_ISSUED"]
  most_recent = true # Use the most recently issued certificate

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
locals {
  # Construct API domain name if not explicitly provided
  effective_api_domain_name = var.api_domain_name != null ? var.api_domain_name : "${var.api_domain_prefix}.${var.domain_name}"
}

resource "aws_apigatewayv2_domain_name" "main" {
  domain_name = local.effective_api_domain_name

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
      condition     = can(regex("\\.", local.effective_api_domain_name))
      error_message = "The API domain name '${local.effective_api_domain_name}' is not a valid domain name."
    }

    # Ensure the domain name is within the certificate's scope
    precondition {
      condition = var.cert_domain == null || (var.cert_domain != null && (
        local.effective_api_domain_name == var.cert_domain ||
        endswith(local.effective_api_domain_name, ".${var.cert_domain}") ||
        (startswith(var.cert_domain, "*") && endswith(local.effective_api_domain_name, substr(var.cert_domain, 1, length(var.cert_domain) - 1)))
      ))
      error_message = "The API domain name '${local.effective_api_domain_name}' is not covered by the certificate domain '${var.cert_domain}'."
    }
  }
}

# API Mapping to connect the domain to the API (only if domain and certificate are configured)
resource "aws_apigatewayv2_api_mapping" "main" {
  api_id      = aws_apigatewayv2_api.main.id
  domain_name = aws_apigatewayv2_domain_name.main.id
  stage       = aws_apigatewayv2_stage.main.id # Point to the main stage
}

# Route53 record for API Gateway custom domain (needed for direct access to API)
# Only create if not using CloudFront routing
resource "aws_route53_record" "api" {
  count = length(aws_apigatewayv2_domain_name.main) > 0 && var.create_route53_record ? 1 : 0

  zone_id = data.aws_route53_zone.main.zone_id
  name    = local.effective_api_domain_name
  type    = "A"

  alias {
    name                   = aws_apigatewayv2_domain_name.main.domain_name_configuration[0].target_domain_name
    zone_id                = aws_apigatewayv2_domain_name.main.domain_name_configuration[0].hosted_zone_id
    evaluate_target_health = false
  }

  allow_overwrite = true
}

# API Gateway HTTP API (HTTP API is cheaper than REST API)
resource "aws_apigatewayv2_api" "main" {
  name          = "${var.app_name}-${var.environment}"
  protocol_type = "HTTP"
  description   = "API Gateway for ${var.app_name} ${var.environment} environment"

  # CORS configuration for Flask Lambda deployment
  cors_configuration {
    # Allow specific origins for credentials support
    allow_origins = var.api_cors_allow_origins

    # HTTP methods for Flask application
    allow_methods = [
      "GET",
      "POST",
      "OPTIONS",
      "PUT",
      "PATCH",
      "DELETE",
      "HEAD"
    ]

    allow_headers = var.api_cors_allow_headers

    # Headers to expose to JavaScript
    expose_headers = var.api_cors_expose_headers

    # Enable/disable credentials for cookie forwarding
    allow_credentials = var.api_cors_allow_credentials

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

  # Access logging settings with enhanced error details
  access_log_settings {
    destination_arn = aws_cloudwatch_log_group.api_gw.arn
    format = jsonencode({
      requestId          = "$context.requestId"
      ip                 = "$context.identity.sourceIp"
      requestTime        = "$context.requestTime"
      requestTimeEpoch   = "$context.requestTimeEpoch"
      httpMethod         = "$context.httpMethod"
      routeKey           = "$context.routeKey"
      path               = "$context.path"
      protocol           = "$context.protocol"
      status             = "$context.status"
      responseLength     = "$context.responseLength"
      responseLatency    = "$context.responseLatency"
      integrationStatus  = "$context.integrationStatus"
      integrationError   = "$context.integrationErrorMessage"
      integrationLatency = "$context.integrationLatency"
      userAgent          = "$context.identity.userAgent"
      error              = "$context.error.message"
      errorResponseType  = "$context.error.responseType"
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
