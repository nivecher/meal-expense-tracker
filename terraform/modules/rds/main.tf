# RDS Instance with optimized settings from original main.tf
resource "aws_db_instance" "main" {
  # Basic configuration - optimized for free tier
  identifier            = "${var.app_name}-${var.environment}"
  allocated_storage     = 20 # Free tier allows up to 20GB
  max_allocated_storage = 20 # Disable storage autoscaling for free tier
  storage_type          = "gp2"
  engine                = "postgres"
  engine_version        = "14.5"
  instance_class        = "db.t3.micro" # Free tier eligible

  # Database credentials
  db_name  = var.app_name
  username = var.app_name
  password = random_password.db_password.result

  # Network configuration
  db_subnet_group_name   = var.db_subnet_group_name
  vpc_security_group_ids = [var.db_security_group_id]

  # Backup & maintenance
  backup_retention_period = 7             # Keep backups for 7 days
  backup_window           = "03:00-03:30" # 30-minute backup window
  maintenance_window      = "sun:04:00-sun:04:30"

  # Performance & cost optimization
  multi_az          = var.environment == "prod" # Only enable Multi-AZ in production
  storage_encrypted = true

  # Security
  skip_final_snapshot = var.environment != "prod" # Don't keep final snapshot in non-prod
  deletion_protection = var.environment == "prod" # Prevent accidental deletion in prod

  # Monitoring
  performance_insights_enabled = true

  # Parameter group
  parameter_group_name = aws_db_parameter_group.main.name

  tags = merge({
    Name = "${var.app_name}-${var.environment}-db"
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

# Store DB credentials in Secrets Manager
resource "aws_secretsmanager_secret" "db_credentials" {
  name = "${var.app_name}/${var.environment}/db-credentials"

  tags = merge({
    Name = "${var.app_name}-${var.environment}-db-credentials"
  }, var.tags)
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
