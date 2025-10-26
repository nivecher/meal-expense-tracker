# Security group for Lambda functions (only created if VPC is configured)
resource "aws_security_group" "lambda" {
  count = var.vpc_id != "" ? 1 : 0

  name        = "${var.app_name}-${var.environment}-lambda-sg"
  description = "Security group for Lambda functions"
  vpc_id      = var.vpc_id

  tags = merge({
    Name = "${var.app_name}-${var.environment}-lambda-sg"
  }, var.tags)

  # No inbound rules needed for Lambda functions as they are triggered by AWS services
  lifecycle {
    create_before_destroy = true
  }
}

# Security Group Rules for Lambda - Restricted Egress
# Only allow outbound traffic to specific AWS services

# Allow HTTPS outbound to VPC endpoints for AWS services (only if VPC is configured)
resource "aws_security_group_rule" "lambda_egress_vpc_https" {
  count = var.vpc_cidr != "" ? 1 : 0

  type              = "egress"
  from_port         = 443
  to_port           = 443
  protocol          = "tcp"
  cidr_blocks       = [var.vpc_cidr]
  security_group_id = aws_security_group.lambda[0].id
  description       = "Allow HTTPS to VPC endpoints for AWS services"
}

# Allow HTTPS outbound to Google APIs (specific IP ranges) - only if VPC is configured
resource "aws_security_group_rule" "lambda_egress_google_apis" {
  count = var.vpc_id != "" ? 1 : 0

  type      = "egress"
  from_port = 443
  to_port   = 443
  protocol  = "tcp"
  cidr_blocks = [
    "142.250.0.0/15", # Google APIs IP range
    "172.217.0.0/16", # Google Maps IP range
    "173.194.0.0/16", # Additional Google services IP range
    "192.178.0.0/16", # Additional Google services IP range
  ]
  security_group_id = aws_security_group.lambda[0].id
  description       = "Allow HTTPS to Google APIs (Places, Maps, Fonts, Static Content)"
}

# Allow Lambda to make DNS queries to Google DNS (8.8.8.8 and 8.8.4.4) - only if VPC is configured
resource "aws_security_group_rule" "egress_dns_udp_google" {
  count = var.vpc_id != "" ? 1 : 0

  type              = "egress"
  from_port         = 53
  to_port           = 53
  protocol          = "udp"
  cidr_blocks       = ["8.8.8.8/32", "8.8.4.4/32"]
  security_group_id = aws_security_group.lambda[0].id
  description       = "Allow DNS (UDP) to Google DNS for external services"
}

resource "aws_security_group_rule" "egress_dns_tcp_google" {
  count = var.vpc_id != "" ? 1 : 0

  type              = "egress"
  from_port         = 53
  to_port           = 53
  protocol          = "tcp"
  cidr_blocks       = ["8.8.8.8/32", "8.8.4.4/32"]
  security_group_id = aws_security_group.lambda[0].id
  description       = "Allow DNS (TCP) to Google DNS for external services"
}
