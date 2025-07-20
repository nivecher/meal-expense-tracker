# Security group for Lambda functions
resource "aws_security_group" "lambda" {
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

# Allow HTTPS outbound for AWS API calls within VPC
resource "aws_security_group_rule" "lambda_egress_https" {
  type              = "egress"
  from_port         = 443
  to_port           = 443
  protocol          = "tcp"
  cidr_blocks       = [var.vpc_cidr]
  security_group_id = aws_security_group.lambda.id
  description       = "Allow HTTPS outbound traffic within VPC"
}

# Allow DNS (UDP) for service discovery within VPC
resource "aws_security_group_rule" "lambda_egress_dns_udp" {
  type              = "egress"
  from_port         = 53
  to_port           = 53
  protocol          = "udp"
  cidr_blocks       = [var.vpc_cidr]
  security_group_id = aws_security_group.lambda.id
  description       = "Allow DNS (UDP) outbound within VPC"
}

# Allow DNS (TCP) for larger DNS responses within VPC
resource "aws_security_group_rule" "lambda_egress_dns_tcp" {
  type              = "egress"
  from_port         = 53
  to_port           = 53
  protocol          = "tcp"
  cidr_blocks       = [var.vpc_cidr]
  security_group_id = aws_security_group.lambda.id
  description       = "Allow DNS (TCP) outbound for large DNS responses"
}

# Allow Lambda to access RDS using security group reference
