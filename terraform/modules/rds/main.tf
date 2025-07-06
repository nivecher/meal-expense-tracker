# AWS provider configuration is handled by the root module
# IAM Role for RDS Enhanced Monitoring
resource "aws_iam_role" "rds_enhanced_monitoring" {
  name = "${var.app_name}-${var.environment}-rds-monitoring-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "monitoring.rds.amazonaws.com"
      }
    }]
  })

  tags = merge({
    Name        = "${var.app_name}-${var.environment}-rds-monitoring-role"
    Environment = var.environment
    ManagedBy   = "terraform"
  }, var.tags)
}

# Attach the AWS managed policy for RDS enhanced monitoring
resource "aws_iam_role_policy_attachment" "rds_enhanced_monitoring" {
  role       = aws_iam_role.rds_enhanced_monitoring.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonRDSEnhancedMonitoringRole"
}

# RDS Instance with cost-optimized settings
resource "aws_db_instance" "main" {
  # Basic configuration - optimized for free tier
  identifier            = "${var.app_name}-${var.environment}"
  allocated_storage     = var.db_allocated_storage
  max_allocated_storage = 100 # Allow storage to grow to 100GB
  storage_type          = "gp2"
  engine                = "postgres"
  engine_version        = "14.18"
  instance_class        = "db.t3.micro" # Free tier eligible

  # Database credentials
  # Ensure db_name and username start with a letter and contain only alphanumeric characters
  db_name  = replace(lower(var.app_name), "/[^a-z0-9]+/", "")
  username = "db_${replace(lower(var.app_name), "/[^a-z0-9]+/", "")}" # Prefix with db_ to ensure it starts with a letter
  password = random_password.db_password.result

  # Network configuration
  db_subnet_group_name   = var.db_subnet_group_name
  vpc_security_group_ids = [aws_security_group.rds.id]
  publicly_accessible    = false  # Keep database private
  network_type           = "IPV4" # Explicitly disable public access

  # Backup & maintenance
  backup_retention_period = 7                     # Keep backups for 7 days
  backup_window           = "03:00-04:00"         # 1-hour backup window
  maintenance_window      = "tue:04:00-tue:05:00" # 1-hour maintenance window after backup
  copy_tags_to_snapshot   = false
  apply_immediately       = true

  # Enable automated backups
  backup_target = "region" # Store backups in the same region as the DB instance

  # Performance & cost optimization
  multi_az          = var.environment == "prod" # Enable Multi-AZ in prod
  storage_encrypted = true                      # Encryption at rest is free

  # Security
  skip_final_snapshot                 = var.environment != "prod" # Don't keep final snapshot in non-prod
  deletion_protection                 = true                      # Enable deletion protection in all environments
  delete_automated_backups            = var.environment != "prod"
  kms_key_id                          = var.db_kms_key_arn
  iam_database_authentication_enabled = true # Enable IAM database authentication

  # Monitoring - enable performance insights with a 7-day retention period
  performance_insights_enabled          = true
  performance_insights_kms_key_id       = var.db_kms_key_arn
  performance_insights_retention_period = 7

  # Enable enhanced monitoring with a 60-second interval
  monitoring_interval = 60
  monitoring_role_arn = aws_iam_role.rds_enhanced_monitoring.arn

  # Parameter group
  parameter_group_name = aws_db_parameter_group.main.name

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
