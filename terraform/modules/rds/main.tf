# AWS provider configuration is handled by the root module
# Note: Removing enhanced monitoring to stay within free tier
# as it incurs additional costs when enabled

# RDS Instance with cost-optimized settings
resource "aws_db_instance" "main" {
  # Basic configuration - optimized for free tier
  identifier            = "${var.app_name}-${var.environment}"
  instance_class        = "db.t3.micro" # Free tier eligible
  allocated_storage     = 20            # Free tier eligible (20GB)
  max_allocated_storage = 20            # Match allocated storage to prevent scaling
  storage_type          = "gp2"         # Free tier eligible
  storage_encrypted     = true
  kms_key_id            = var.db_kms_key_arn
  engine                = "postgres"
  engine_version        = "14.18" # Latest free tier eligible version
  parameter_group_name  = aws_db_parameter_group.main.name

  # Database credentials
  # Ensure db_name and username start with a letter and contain only alphanumeric characters
  db_name  = replace(lower(var.app_name), "/[^a-z0-9]+/", "")
  username = "db_${replace(lower(var.app_name), "/[^a-z0-9]+/", "")}" # Prefix with db_ to ensure it starts with a letter
  password = random_password.db_password.result

  # Network configuration
  db_subnet_group_name   = var.db_subnet_group_name
  vpc_security_group_ids = [aws_security_group.rds.id]
  publicly_accessible    = var.db_publicly_accessible
  network_type           = "IPV4"
  multi_az               = false # Disable Multi-AZ for free tier

  # Backup & maintenance
  backup_retention_period = 7                     # Keep backups for 7 days (free tier)
  backup_window           = "03:00-04:00"         # 1-hour backup window
  maintenance_window      = "tue:04:00-tue:05:00" # 1-hour maintenance window after backup
  copy_tags_to_snapshot   = true
  apply_immediately       = true
  skip_final_snapshot     = true  # Skip final snapshot to avoid costs (not recommended for production)
  deletion_protection     = false # Disable deletion protection to avoid manual steps when deleting

  # Security
  iam_database_authentication_enabled = true # Enable IAM database authentication

  # Monitoring - disable performance insights for free tier
  performance_insights_enabled = false
  monitoring_interval          = 0 # Disable enhanced monitoring for free tier

  tags = merge({
    Name        = "${var.app_name}-${var.environment}-db"
    Environment = var.environment
    ManagedBy   = "terraform"
    CostCenter  = var.app_name
  }, var.tags)
}

# DB Parameter Group
resource "aws_db_parameter_group" "main" {
  name   = "${var.app_name}-${var.environment}-pg"
  family = "postgres14"

  parameter {
    name  = "log_connections"
    value = "1"
  }

  parameter {
    name  = "log_min_duration_statement"
    value = "1000" # Log slow queries > 1s
  }

  tags = var.tags
}

# Random password for DB
resource "random_password" "db_password" {
  length  = 32
  special = false # Avoid special chars that might cause issues
}

// TODO add secret rotation

# Store DB credentials in Secrets Manager with KMS encryption
resource "aws_secretsmanager_secret" "db_credentials" {
  name        = "${var.app_name}/${var.environment}/db-credentials"
  description = "Database credentials for ${var.app_name} ${var.environment} environment"
  kms_key_id  = var.db_kms_key_arn

  tags = merge({
    Name = "${var.app_name}-${var.environment}-db-credentials"
  }, var.tags)

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_secretsmanager_secret_version" "db_credentials" {
  secret_id = aws_secretsmanager_secret.db_credentials.id
  secret_string = jsonencode({
    db_host     = aws_db_instance.main.address
    db_port     = aws_db_instance.main.port
    db_name     = aws_db_instance.main.db_name
    db_username = aws_db_instance.main.username
    db_password = aws_db_instance.main.password
  })
}
