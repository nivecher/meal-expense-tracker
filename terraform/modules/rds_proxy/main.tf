# RDS Proxy for Aurora Serverless
# Provides connection pooling and improved performance

resource "aws_db_proxy" "aurora" {
  name                = "${var.app_name}-${var.environment}-aurora-proxy"
  debug_logging       = var.debug_logging
  engine_family       = "POSTGRESQL"
  idle_client_timeout = var.idle_client_timeout
  require_tls         = true

  role_arn = aws_iam_role.rds_proxy_role.arn

  vpc_security_group_ids = [aws_security_group.rds_proxy.id]
  vpc_subnet_ids         = var.private_subnet_ids

  # Authentication configuration
  auth {
    auth_scheme = "SECRETS"
    description = "Authentication using Secrets Manager"
    iam_auth    = "DISABLED"
    secret_arn  = var.aurora_secrets_arn
  }

  tags = merge({
    Name        = "${var.app_name}-${var.environment}-aurora-proxy"
    Environment = var.environment
    ManagedBy   = "terraform"
    Type        = "rds-proxy"
  }, var.tags)
}

# RDS Proxy target group for Aurora cluster
resource "aws_db_proxy_default_target_group" "aurora" {
  db_proxy_name = aws_db_proxy.aurora.name

  connection_pool_config {
    max_connections_percent      = var.max_connections_percent
    max_idle_connections_percent = var.max_idle_connections_percent
    connection_borrow_timeout    = var.connection_borrow_timeout
  }
}

# RDS Proxy default target group (automatically created)
# The proxy will automatically connect to the Aurora cluster

# IAM role for RDS Proxy
resource "aws_iam_role" "rds_proxy_role" {
  name = "${var.app_name}-${var.environment}-rds-proxy-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "rds.amazonaws.com"
        }
      }
    ]
  })

  tags = merge({
    Name        = "${var.app_name}-${var.environment}-rds-proxy-role"
    Environment = var.environment
    ManagedBy   = "terraform"
  }, var.tags)
}

# IAM policy for RDS Proxy
resource "aws_iam_role_policy" "rds_proxy_policy" {
  name = "${var.app_name}-${var.environment}-rds-proxy-policy"
  role = aws_iam_role.rds_proxy_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue",
          "secretsmanager:DescribeSecret"
        ]
        Resource = var.aurora_secrets_arn
      },
      {
        Effect = "Allow"
        Action = [
          "kms:Decrypt"
        ]
        Resource = var.kms_key_arn
        Condition = {
          StringEquals = {
            "kms:ViaService" = "secretsmanager.${var.aws_region}.amazonaws.com"
          }
        }
      }
    ]
  })
}

# Security group for RDS Proxy
resource "aws_security_group" "rds_proxy" {
  name        = "${var.app_name}-${var.environment}-rds-proxy-sg"
  description = "Security group for RDS Proxy"
  vpc_id      = var.vpc_id

  tags = merge({
    Name        = "${var.app_name}-${var.environment}-rds-proxy-sg"
    Environment = var.environment
    ManagedBy   = "terraform"
  }, var.tags)
}

# Security group rules for RDS Proxy
resource "aws_security_group_rule" "rds_proxy_egress" {
  type              = "egress"
  from_port         = 5432
  to_port           = 5432
  protocol          = "tcp"
  security_group_id = aws_security_group.rds_proxy.id
  description       = "Allow RDS Proxy to connect to Aurora PostgreSQL"

  # Allow connection to Aurora security group
  source_security_group_id = var.aurora_security_group_id
}

# CloudWatch alarms for RDS Proxy monitoring
resource "aws_cloudwatch_metric_alarm" "rds_proxy_connections" {
  count = var.enable_monitoring ? 1 : 0

  alarm_name          = "${var.app_name}-${var.environment}-rds-proxy-connections"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "DatabaseConnections"
  namespace           = "AWS/RDS"
  period              = "300"
  statistic           = "Maximum"
  threshold           = var.connection_threshold
  alarm_description   = "RDS Proxy has too many connections"
  alarm_actions       = []

  dimensions = {
    DBProxyName = aws_db_proxy.aurora.name
  }

  tags = merge({
    Name        = "${var.app_name}-${var.environment}-rds-proxy-connections-alarm"
    Environment = var.environment
    ManagedBy   = "terraform"
  }, var.tags)
}

resource "aws_cloudwatch_metric_alarm" "rds_proxy_client_connections" {
  count = var.enable_monitoring ? 1 : 0

  alarm_name          = "${var.app_name}-${var.environment}-rds-proxy-client-connections"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "ClientConnections"
  namespace           = "AWS/RDS"
  period              = "300"
  statistic           = "Maximum"
  threshold           = var.client_connection_threshold
  alarm_description   = "RDS Proxy has too many client connections"
  alarm_actions       = []

  dimensions = {
    DBProxyName = aws_db_proxy.aurora.name
  }

  tags = merge({
    Name        = "${var.app_name}-${var.environment}-rds-proxy-client-connections-alarm"
    Environment = var.environment
    ManagedBy   = "terraform"
  }, var.tags)
}
