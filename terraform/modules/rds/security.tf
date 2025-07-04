# Security group for RDS
resource "aws_security_group" "rds" {
  name        = "${var.app_name}-${var.environment}-rds-sg"
  description = "Security group for RDS instance"
  vpc_id      = var.vpc_id

  # Inbound rule: Allow PostgreSQL access from within VPC
  ingress {
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"
    cidr_blocks = [var.vpc_cidr]
    description = "Allow PostgreSQL access from within VPC"
  }

  # Inbound rule: Allow PostgreSQL access from Lambda security group if provided
  dynamic "ingress" {
    for_each = var.lambda_security_group_id != null ? [1] : []


    content {
      from_port       = 5432
      to_port         = 5432
      protocol        = "tcp"
      security_groups = [var.lambda_security_group_id]
      description     = "Allow PostgreSQL access from Lambda security group"
    }
  }

  # Restrict outbound traffic to only necessary destinations
  egress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = [var.vpc_cidr]
    description = "Allow outbound HTTPS traffic within VPC for AWS services"
  }

  # Allow outbound traffic to Secrets Manager VPC endpoint if used
  dynamic "egress" {
    for_each = var.secrets_manager_prefix_list_id != "" ? [1] : []

    content {
      from_port       = 443
      to_port         = 443
      protocol        = "tcp"
      prefix_list_ids = [var.secrets_manager_prefix_list_id]
      description     = "Allow outbound HTTPS to Secrets Manager VPC endpoint"
    }
  }

  # Allow outbound traffic to CloudWatch Logs VPC endpoint if used
  dynamic "egress" {
    for_each = var.cloudwatch_logs_prefix_list_id != "" ? [1] : []

    content {
      from_port       = 443
      to_port         = 443
      protocol        = "tcp"
      prefix_list_ids = [var.cloudwatch_logs_prefix_list_id]
      description     = "Allow outbound HTTPS to CloudWatch Logs VPC endpoint"
    }
  }

  tags = merge({
    Name = "${var.app_name}-${var.environment}-rds-sg"
  }, var.tags)
}
