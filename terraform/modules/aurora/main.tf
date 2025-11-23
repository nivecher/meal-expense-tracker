# Aurora Serverless v2 PostgreSQL Cluster
# This replaces the RDS PostgreSQL instance with Aurora Serverless for cost efficiency

resource "aws_rds_cluster" "main" {
  cluster_identifier = "${var.app_name}-${var.environment}-aurora"
  engine             = "aurora-postgresql"
  engine_version     = "15.4" # Latest stable Aurora PostgreSQL version

  # Enable Aurora Serverless v2 scaling
  serverlessv2_scaling_configuration {
    min_capacity = 0.5 # Minimum ACUs (cost optimization for dev)
    max_capacity = 2   # Maximum ACUs (can scale up to 16 for production)
  }

  # Enable Data API for Query Editor access
  enable_http_endpoint = true

  # Database credentials from Secrets Manager
  master_username = var.db_username
  master_password = var.db_password
  database_name   = var.db_name # Required for Aurora cluster

  # Network configuration (same VPC as current RDS)
  db_subnet_group_name   = var.db_subnet_group_name
  vpc_security_group_ids = [aws_security_group.aurora.id]

  # Use custom parameter group instead of default
  db_cluster_parameter_group_name = aws_rds_cluster_parameter_group.main.name

  # Backup and maintenance (cost-optimized)
  backup_retention_period      = var.backup_retention_period # 7 days (same as RDS)
  preferred_backup_window      = "03:00-04:00"
  preferred_maintenance_window = "tue:04:00-tue:05:00"

  # Security
  storage_encrypted                   = true
  kms_key_id                          = var.kms_key_arn
  iam_database_authentication_enabled = true

  # Cost optimization
  deletion_protection   = var.deletion_protection # false for dev, true for prod
  copy_tags_to_snapshot = true
  skip_final_snapshot   = true # Skip final snapshot to avoid costs
  # final_snapshot_identifier not needed when skip_final_snapshot = true

  # Performance insights disabled for cost savings (enable if needed)
  performance_insights_enabled = false

  tags = merge({
    Name        = "${var.app_name}-${var.environment}-aurora-cluster"
    Environment = var.environment
    ManagedBy   = "terraform"
    CostCenter  = var.app_name
    Type        = "aurora-serverless-v2"
  }, var.tags)

  lifecycle {
    ignore_changes = [
      # Allow Aurora to manage these attributes
      engine_version,
      skip_final_snapshot,
      deletion_protection,
      backup_retention_period,
    ]
  }
}

# Aurora cluster instance (Serverless v2 compatible)
resource "aws_rds_cluster_instance" "main" {
  identifier         = "${var.app_name}-${var.environment}-aurora-instance"
  cluster_identifier = aws_rds_cluster.main.id
  instance_class     = "db.serverless" # Serverless v2 instance class
  engine             = aws_rds_cluster.main.engine
  engine_version     = aws_rds_cluster.main.engine_version

  # Performance insights (disabled for cost)
  performance_insights_enabled = false

  tags = merge({
    Name        = "${var.app_name}-${var.environment}-aurora-instance"
    Environment = var.environment
    ManagedBy   = "terraform"
    Type        = "aurora-serverless-v2"
  }, var.tags)
}

# Security group for Aurora cluster
resource "aws_security_group" "aurora" {
  name        = "${var.app_name}-${var.environment}-aurora-sg"
  description = "Security group for Aurora Serverless cluster"
  vpc_id      = var.vpc_id

  tags = merge({
    Name        = "${var.app_name}-${var.environment}-aurora-sg"
    Environment = var.environment
    ManagedBy   = "terraform"
  }, var.tags)
}

# Security group rules for Aurora
resource "aws_security_group_rule" "aurora_ingress_lambda" {
  count                    = var.lambda_security_group_id != "" ? 1 : 0
  type                     = "ingress"
  from_port                = 5432
  to_port                  = 5432
  protocol                 = "tcp"
  security_group_id        = aws_security_group.aurora.id
  source_security_group_id = var.lambda_security_group_id
  description              = "Allow Lambda functions to access Aurora PostgreSQL"
}

# Allow Aurora to make outbound connections (for extensions, etc.)
resource "aws_security_group_rule" "aurora_egress" {
  type              = "egress"
  from_port         = 0
  to_port           = 0
  protocol          = "-1"
  cidr_blocks       = ["0.0.0.0/0"]
  security_group_id = aws_security_group.aurora.id
  description       = "Allow all outbound traffic from Aurora"
}

# DB parameter group for Aurora PostgreSQL
resource "aws_rds_cluster_parameter_group" "main" {
  family = "aurora-postgresql15"
  name   = "${var.app_name}-${var.environment}-aurora-pg"

  parameter {
    name  = "log_connections"
    value = "1"
  }

  parameter {
    name  = "log_min_duration_statement"
    value = "1000" # Log slow queries > 1s
  }

  # Aurora-specific parameters for performance
  parameter {
    name         = "shared_preload_libraries"
    value        = "pg_stat_statements"
    apply_method = "immediate"
  }

  tags = merge({
    Name        = "${var.app_name}-${var.environment}-aurora-pg"
    Environment = var.environment
    ManagedBy   = "terraform"
  }, var.tags)

  # Aurora parameter groups often require cluster reboots for changes to take effect
  # Ignore changes to prevent constant drift detection
  lifecycle {
    ignore_changes = [
      parameter,
    ]
  }
}

# Store Aurora credentials in Secrets Manager
resource "aws_secretsmanager_secret" "aurora_credentials" {
  name        = "${var.app_name}/${var.environment}/aurora-credentials"
  description = "Database credentials for Aurora Serverless cluster"
  kms_key_id  = var.kms_key_arn

  tags = merge({
    Name        = "${var.app_name}-${var.environment}-aurora-credentials"
    Environment = var.environment
    ManagedBy   = "terraform"
  }, var.tags)

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_secretsmanager_secret_version" "aurora_credentials" {
  secret_id = aws_secretsmanager_secret.aurora_credentials.id
  secret_string = jsonencode({
    db_host     = aws_rds_cluster.main.endpoint
    db_port     = aws_rds_cluster.main.port
    db_name     = aws_rds_cluster.main.database_name
    db_username = aws_rds_cluster.main.master_username
    db_password = var.db_password
    db_engine   = "aurora-postgresql"
  })
}

# CloudWatch alarms for Aurora monitoring
resource "aws_cloudwatch_metric_alarm" "aurora_cpu" {
  alarm_name          = "${var.app_name}-${var.environment}-aurora-cpu"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "CPUUtilization"
  namespace           = "AWS/RDS"
  period              = "300"
  statistic           = "Average"
  threshold           = "80"
  alarm_description   = "Aurora CPU utilization is above 80%"
  alarm_actions       = []

  dimensions = {
    DBClusterIdentifier = aws_rds_cluster.main.cluster_identifier
  }

  tags = merge({
    Name        = "${var.app_name}-${var.environment}-aurora-cpu-alarm"
    Environment = var.environment
    ManagedBy   = "terraform"
  }, var.tags)
}

resource "aws_cloudwatch_metric_alarm" "aurora_connections" {
  alarm_name          = "${var.app_name}-${var.environment}-aurora-connections"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "DatabaseConnections"
  namespace           = "AWS/RDS"
  period              = "300"
  statistic           = "Maximum"
  threshold           = "50"
  alarm_description   = "Aurora has too many connections"
  alarm_actions       = []

  dimensions = {
    DBClusterIdentifier = aws_rds_cluster.main.cluster_identifier
  }

  tags = merge({
    Name        = "${var.app_name}-${var.environment}-aurora-connections-alarm"
    Environment = var.environment
    ManagedBy   = "terraform"
  }, var.tags)
}
