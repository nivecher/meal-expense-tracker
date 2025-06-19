# Look up the existing Route53 zone if domain_name is provided
data "aws_route53_zone" "main" {
  count        = var.domain_name != null ? 1 : 0
  name         = var.domain_name
  private_zone = false
}

# Look up the existing ACM certificate in us-east-1 if cert_domain is provided
data "aws_acm_certificate" "main" {
  count    = var.cert_domain != null ? 1 : 0
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
  count       = var.domain_name != null && length(data.aws_acm_certificate.main) > 0 ? 1 : 0
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

  lifecycle {
    # Prevent accidental deletion of the custom domain
    prevent_destroy = true

    # Ensure we have a valid domain name configuration
    precondition {
      condition     = can(regex("^[a-zA-Z0-9][a-zA-Z0-9-]{1,61}[a-zA-Z0-9](?:\\.(?:[a-zA-Z0-9-]+\\.)*[a-zA-Z]{2,})?$", var.api_domain_name))
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
  count       = var.domain_name != null ? 1 : 0
  api_id      = aws_apigatewayv2_api.main.id
  domain_name = aws_apigatewayv2_domain_name.main[0].id
  stage       = aws_apigatewayv2_stage.main.id # Point to the main stage
}

# Create Route53 record for the API Gateway custom domain (only if domain and certificate are configured)
resource "aws_route53_record" "api" {
  count   = var.domain_name != null ? 1 : 0
  zone_id = data.aws_route53_zone.main[0].zone_id
  name    = trimsuffix(var.api_domain_name, ".${var.domain_name}")
  type    = "A"

  alias {
    name                   = aws_apigatewayv2_domain_name.main[0].domain_name_configuration[0].target_domain_name
    zone_id                = aws_apigatewayv2_domain_name.main[0].domain_name_configuration[0].hosted_zone_id
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
      condition     = aws_apigatewayv2_domain_name.main[0].domain_name_configuration[0].target_domain_name != ""
      error_message = "The target domain name for the API Gateway custom domain is empty."
    }
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
    throttling_burst_limit   = 100
    throttling_rate_limit    = 100
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
  retention_in_days = 30
  kms_key_id        = var.logs_kms_key_arn

  tags = merge({
    Name        = "${var.app_name}-${var.environment}-api-gw-logs"
    Environment = var.environment
    ManagedBy   = "terraform"
  }, var.tags)
}

# API Gateway Lambda Integration (only if lambda_invoke_arn is provided)
resource "aws_apigatewayv2_integration" "lambda" {
  count = var.lambda_invoke_arn != null ? 1 : 0

  api_id             = aws_apigatewayv2_api.main.id
  integration_type   = "AWS_PROXY"
  integration_method = "POST"
  integration_uri    = var.lambda_invoke_arn
}

# Allow API Gateway to invoke the Lambda function
resource "aws_lambda_permission" "api_gateway" {
  count = var.lambda_invoke_arn != null && var.lambda_function_name != null ? 1 : 0

  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = var.lambda_function_name
  principal     = "apigateway.amazonaws.com"

  # The /*/* part allows invocation from any stage and method
  # within the API Gateway HTTP API
  source_arn = "${aws_apigatewayv2_api.main.execution_arn}/*/*"
}

# Add a catch-all {proxy+} route
resource "aws_apigatewayv2_route" "proxy" {
  count = var.lambda_invoke_arn != null ? 1 : 0

  api_id    = aws_apigatewayv2_api.main.id
  route_key = "ANY /{proxy+}"
  target    = "integrations/${aws_apigatewayv2_integration.lambda[0].id}"
}

# Add a root route
resource "aws_apigatewayv2_route" "root" {
  count = var.lambda_invoke_arn != null ? 1 : 0

  api_id    = aws_apigatewayv2_api.main.id
  route_key = "ANY /"
  target    = "integrations/${aws_apigatewayv2_integration.lambda[0].id}"
}

# Note: Route responses are not supported for HTTP API with proxy integration
# The API will automatically handle responses from the Lambda function
