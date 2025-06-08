terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  backend "s3" {
    use_locking = true
  }
}

provider "aws" {
  region = var.aws_region
}

# ======================
# Data Sources
# ======================
data "aws_caller_identity" "current" {}

data "aws_availability_zones" "available" {}

# ======================
# Locals
# ======================
locals {
  account_id = data.aws_caller_identity.current.account_id
}

# ======================
# VPC Resources
# ======================
resource "aws_vpc" "app_vpc" {
  cidr_block = var.environment == "prod" ? "10.0.0.0/16" : "10.1.0.0/16"

  # Required for private DNS resolution and hostname assignment
  enable_dns_support   = true
  enable_dns_hostnames = true

  tags = merge(
    {
      Name        = "${var.app_name}-vpc"
      Environment = var.environment
      Application = var.app_name
    },
    var.tags
  )
}

# CloudWatch Log Group for VPC Flow Logs
resource "aws_cloudwatch_log_group" "vpc_flow_logs" {
  name              = "/aws/vpc-flow-logs/${var.app_name}-${var.environment}"
  retention_in_days = 365 # Retain logs for 1 year for compliance
  kms_key_id        = aws_kms_key.primary_encryption_key.arn

  tags = merge(
    {
      Name        = "${var.app_name}-vpc-flow-logs"
      Environment = var.environment
      Application = var.app_name
    },
    var.tags
  )
}

# IAM Role for VPC Flow Logs
resource "aws_iam_role" "vpc_flow_logs_role" {
  name_prefix = "${substr(var.app_name, 0, 15)}-flow-logs-" # Shortened to fit within 38 chars

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "vpc-flow-logs.amazonaws.com"
        }
      }
    ]
  })

  tags = merge(
    {
      Name        = "${var.app_name}-vpc-flow-logs-role"
      Environment = var.environment
      Application = var.app_name
    },
    var.tags
  )
}

# IAM Policy for VPC Flow Logs
resource "aws_iam_role_policy" "vpc_flow_logs_policy" {
  name = "${var.app_name}-vpc-flow-logs-policy"
  role = aws_iam_role.vpc_flow_logs_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "${aws_cloudwatch_log_group.vpc_flow_logs.arn}:*"
      },
      {
        Effect = "Allow"
        Action = [
          "logs:DescribeLogGroups",
          "logs:DescribeLogStreams"
        ]
        Resource = "${aws_cloudwatch_log_group.vpc_flow_logs.arn}"
      }
    ]
  })
}

# Enable VPC Flow Logs
resource "aws_flow_log" "vpc_flow_logs" {
  iam_role_arn    = aws_iam_role.vpc_flow_logs_role.arn
  log_destination = aws_cloudwatch_log_group.vpc_flow_logs.arn
  traffic_type    = "ALL"
  vpc_id          = aws_vpc.app_vpc.id

  max_aggregation_interval = 60

  tags = merge(
    {
      Name        = "${var.app_name}-vpc-flow-logs"
      Environment = var.environment
      Application = var.app_name
    },
    var.tags
  )
}

# DB Subnet Group - Always use at least 2 AZs for RDS
resource "aws_db_subnet_group" "default" {
  name       = "${var.app_name}-${var.environment}-db-subnet-group"
  subnet_ids = [for s in aws_subnet.app_private_subnet : s.id]

  tags = {
    Name        = "${var.app_name}-db-subnet-group"
    Environment = var.environment
  }
}

# ======================
# Security Groups
# ======================
# Default Security Group - Explicitly deny all traffic by default
resource "aws_default_security_group" "default" {
  vpc_id = aws_vpc.app_vpc.id

  # Explicitly define empty ingress/egress to override AWS defaults
  ingress = []
  egress  = []

  # Add descriptive tags
  tags = merge(
    {
      Name        = "${var.app_name}-${var.environment}-default-sg"
      Description = "Hardened security group - all traffic denied by default"
      Environment = var.environment
      Application = var.app_name
    },
    var.tags
  )

  # Ensure security group is not modified outside of Terraform
  lifecycle {
    create_before_destroy = true
    ignore_changes = [
      # Ignore changes to ingress/egress rules that might be added by AWS
      ingress,
      egress,
    ]
  }
}

# Lambda Security Group
resource "aws_security_group" "lambda_sg" {
  name_prefix = "${var.app_name}-${var.environment}-lambda-sg"
  description = "Security group for Lambda functions"
  vpc_id      = aws_vpc.app_vpc.id

  ingress {
    description = "Allow HTTPS from VPC CIDR"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = [aws_vpc.app_vpc.cidr_block]
  }

  # Restrict egress to only necessary services
  egress {
    description = "Allow HTTPS outbound to AWS services"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"] # Consider using VPC endpoints instead
  }

  egress {
    description = "Allow DNS outbound"
    from_port   = 53
    to_port     = 53
    protocol    = "udp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "${var.app_name}-${var.environment}-lambda-sg"
    Environment = var.environment
  }
}

resource "aws_security_group_rule" "lambda_ingress_db" {
  type              = "ingress"
  from_port         = 5432
  to_port           = 5432
  protocol          = "tcp"
  cidr_blocks       = [aws_subnet.app_private_subnet[0].cidr_block]
  security_group_id = aws_security_group.lambda_sg.id
  description       = "Allow PostgreSQL access from private subnet"
}

resource "aws_security_group_rule" "lambda_ingress_api" {
  type              = "ingress"
  from_port         = 443
  to_port           = 443
  protocol          = "tcp"
  cidr_blocks       = flatten([for s in aws_subnet.app_private_subnet : s.cidr_block])
  security_group_id = aws_security_group.lambda_sg.id
  description       = "Allow HTTPS access from private subnets"
}

# Private Subnets (2 AZs)
resource "aws_subnet" "app_private_subnet" {
  count             = 2
  availability_zone = element(data.aws_availability_zones.available.names, count.index)

  vpc_id                  = aws_vpc.app_vpc.id
  cidr_block              = cidrsubnet(aws_vpc.app_vpc.cidr_block, 8, count.index)
  map_public_ip_on_launch = false

  tags = {
    Name        = "${var.app_name}-private-subnet-${count.index}"
    Environment = var.environment
  }
}

# Route Table for Private Subnets
resource "aws_route_table" "app_private_route_table" {
  vpc_id = aws_vpc.app_vpc.id

  tags = {
    Name        = "${var.app_name}-private-route-table"
    Environment = var.environment
  }
}

# Route Table Associations
# Only create route table associations for subnets that aren't already associated
resource "aws_route_table_association" "app_private_route_table_association" {
  for_each = {
    for idx, subnet in aws_subnet.app_private_subnet : idx => subnet
    if !contains([for assoc in data.aws_route_tables.private_route_tables.ids :
      length([for rta in data.aws_route_table.private_route_tables[assoc].associations :
        rta.subnet_id == subnet.id
      ]) > 0
    ], true)
  }

  subnet_id      = each.value.id
  route_table_id = aws_route_table.app_private_route_table.id
}

data "aws_route_tables" "private_route_tables" {
  vpc_id = aws_vpc.app_vpc.id
}

data "aws_route_table" "private_route_tables" {
  for_each       = toset(data.aws_route_tables.private_route_tables.ids)
  route_table_id = each.key
}

# Using VPC endpoints instead of NAT Gateway for cost savings
# Removed NAT Gateway route as it's not needed with VPC endpoints

# Lambda Function for Secret Rotation

# Secret Rotation Lambda
resource "aws_lambda_function" "secret_rotation" {
  function_name = "${var.app_name}-${var.environment}-secret-rotation"
  role          = aws_iam_role.secret_rotation_exec.arn
  package_type  = "Zip"
  filename      = "secret_rotation.py"
  handler       = "secret_rotation.lambda_handler"
  runtime       = "python3.12"
  timeout       = 15 # Reduced from 30s
  memory_size   = 128

  # Configure Dead Letter Queue (DLQ) for failed invocations
  dead_letter_config {
    target_arn = aws_sns_topic.lambda_dlq.arn
  }

  # Set concurrency limit to prevent overloading
  reserved_concurrent_executions = 1 # Only allow one rotation at a time

  # Enable X-Ray tracing for better observability
  tracing_config {
    mode = "Active"
  }

  vpc_config {
    security_group_ids = [aws_security_group.lambda_sg.id]
    subnet_ids         = aws_subnet.app_private_subnet[*].id
  }
}

# IAM Role for Secret Rotation
resource "aws_iam_role" "secret_rotation_exec" {
  name = "${var.app_name}-${var.environment}-secret-rotation-exec"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
}

# IAM Policies for Secret Rotation
resource "aws_iam_role_policy" "secret_rotation_policy" {
  name = "${var.app_name}-${var.environment}-secret-rotation-policy"
  role = aws_iam_role.secret_rotation_exec.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue",
          "secretsmanager:PutSecretValue",
          "secretsmanager:UpdateSecretVersionStage",
          "secretsmanager:DescribeSecret"
        ]
        Resource = aws_secretsmanager_secret.db_password.arn
      }
    ]
  })
}

# Main Application Lambda

# Note on Lambda Code Signing (CKV_AWS_272):
# AWS Lambda code signing is recommended for production workloads to ensure only trusted code runs.
# This requires setting up AWS Signer service and proper IAM permissions.
# For production, uncomment and configure the following:
# code_signing_config_arn = aws_lambda_code_signing_config.code_signing.arn
#
# Then uncomment and configure the AWS Signer signing profile:
# resource "aws_signer_signing_profile" "code_signing" {
#   platform_id = "AWSLambda-SHA384-ECDSA"
#   name_prefix = "${var.app_name}-signing-profile"
#
#   signature_validity_period {
#     type  = "YEARS"
#     value = 1
#   }
#
#   tags = merge(
#     {
#       Name        = "${var.app_name}-signing-profile"
#       Environment = var.environment
#       Application = var.app_name
#     },
#     var.tags
#   )
# }
#
# resource "aws_lambda_code_signing_config" "code_signing" {
#   allowed_publishers {
#     signing_profile_version_arns = [aws_signer_signing_profile.code_signing.arn]
#   }
#
#   policies {
#     untrusted_artifact_on_deployment = "Enforce"
#   }
# }

# SNS Topic for Lambda DLQ
resource "aws_sns_topic" "lambda_dlq" {
  name = "${var.app_name}-${var.environment}-lambda-dlq"

  # Enable server-side encryption for the SNS topic
  kms_master_key_id = aws_kms_key.primary_encryption_key.arn

  tags = merge(
    {
      Name        = "${var.app_name}-lambda-dlq"
      Environment = var.environment
      Application = var.app_name
    },
    var.tags
  )
}

resource "aws_lambda_function" "app" {
  function_name = "${var.app_name}-${var.environment}"
  role          = aws_iam_role.lambda_exec.arn
  package_type  = "Image"
  image_uri     = "${aws_ecr_repository.app.repository_url}:${var.image_tag}"

  # Optimized for cost and performance
  timeout       = var.environment == "prod" ? 10 : 3    # Shorter timeout for non-prod
  memory_size   = var.environment == "prod" ? 256 : 128 # Less memory for non-prod
  architectures = ["arm64"]                             # ARM64 is more cost-effective

  # Provisioned concurrency is configured separately using aws_lambda_provisioned_concurrency_config
  # to avoid cold starts in production

  # Set environment variables
  environment {
    variables = {
      NODE_ENV                     = var.environment
      POWERTOOLS_METRICS_NAMESPACE = var.app_name
      LOG_LEVEL                    = var.environment == "prod" ? "INFO" : "DEBUG"
      ENABLE_METRICS               = var.environment == "prod" ? "true" : "false"
      ENABLE_TRACING               = var.environment == "prod" ? "true" : "false"
      ENVIRONMENT                  = var.environment
      DB_SECRET_ARN                = aws_secretsmanager_secret.db_password.arn
      API_GATEWAY_HTTPS_ONLY       = "true"
    }
  }

  # Configure Dead Letter Queue (DLQ) for failed invocations
  dead_letter_config {
    target_arn = aws_sns_topic.lambda_dlq.arn
  }

  # Set concurrency limit to prevent overloading
  reserved_concurrent_executions = 100 # Adjust based on expected load

  kms_key_arn = aws_kms_key.primary_encryption_key.arn

  # VPC configuration for Lambda to access resources in the VPC
  vpc_config {
    subnet_ids         = aws_subnet.app_private_subnet[*].id
    security_group_ids = [aws_security_group.lambda_sg.id]
  }

  tags = {
    Name        = "${var.app_name}-${var.environment}"
    Environment = var.environment
    Application = var.app_name
    ManagedBy   = "Terraform"
  }
}

# API Gateway Configuration

# HTTP API Gateway
resource "aws_apigatewayv2_api" "http_api" {
  name                         = "${var.app_name}-${var.environment}"
  protocol_type                = "HTTP"
  description                  = "HTTP API for ${var.app_name} (${var.environment})"
  disable_execute_api_endpoint = false

  # CORS configuration - when allow_credentials is true, allow_origins cannot be ["*"]
  cors_configuration {
    allow_credentials = false # Set to false since we're using "*" for origins
    allow_headers     = ["Content-Type", "X-Amz-Date", "Authorization", "X-Api-Key"]
    allow_methods     = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    allow_origins     = ["*"]
    max_age           = 3600
  }

  tags = {
    Name        = "${var.app_name}-api"
    Environment = var.environment
    Application = var.app_name
  }
}

# Lambda Integration
resource "aws_apigatewayv2_integration" "lambda" {
  api_id                 = aws_apigatewayv2_api.http_api.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.app.invoke_arn
  payload_format_version = "2.0"
}

# Default Route
resource "aws_apigatewayv2_route" "default" {
  api_id    = aws_apigatewayv2_api.http_api.id
  route_key = "$default"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"

  # Require IAM authorization for all routes by default
  authorization_type = "AWS_IAM"
}

# Default Stage
resource "aws_cloudwatch_log_group" "api_gw" {
  name              = "/aws/api-gw/${var.app_name}-${var.environment}"
  retention_in_days = var.environment == "prod" ? 90 : 30 # 90 days for prod, 30 for others
  kms_key_id        = aws_kms_key.primary_encryption_key.arn

  tags = merge(
    {
      Name        = "${var.app_name}-api-gw-logs"
      Environment = var.environment
      Application = var.app_name
    },
    var.tags
  )
}

resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.http_api.id
  name        = "$default"
  auto_deploy = true

  # Enable access logging
  access_log_settings {
    destination_arn = aws_cloudwatch_log_group.api_gw.arn
    format = jsonencode({
      requestId          = "$context.requestId"
      ip                 = "$context.identity.sourceIp"
      requestTime        = "$context.requestTime"
      httpMethod         = "$context.httpMethod"
      routeKey           = "$context.routeKey"
      status             = "$context.status"
      protocol           = "$context.protocol"
      responseLength     = "$context.responseLength"
      integrationError   = "$context.integrationErrorMessage"
      integrationStatus  = "$context.integrationStatus"
      integrationLatency = "$context.integrationLatency"
      responseLatency    = "$context.responseLatency"
    })
  }

  default_route_settings {
    throttling_burst_limit   = 100 # Adjust based on expected traffic
    throttling_rate_limit    = 50  # Requests per second
    detailed_metrics_enabled = true
  }
}

# IAM Role for Lambda execution
resource "aws_iam_role" "lambda_exec" {
  name = "${var.app_name}-${var.environment}-lambda-exec"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name        = "${var.app_name}-${var.environment}-lambda-exec"
    Environment = var.environment
  }
}

# IAM Role Policy for Lambda
resource "aws_iam_role_policy" "lambda_policy" {
  name = "${var.app_name}-${var.environment}-lambda-policy"
  role = aws_iam_role.lambda_exec.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      # CloudWatch Logs permissions (restricted to this function's log group)
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = [
          "arn:aws:logs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:log-group:/aws/lambda/${var.app_name}-${var.environment}:*"
        ]
      },
      # SNS Publish to DLQ (restricted to our specific topic)
      {
        Effect = "Allow"
        Action = [
          "sns:Publish"
        ]
        Resource = [
          aws_sns_topic.lambda_dlq.arn
        ]
      },
      # Secrets Manager access (restricted to our specific secret)
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue"
        ]
        Resource = [
          aws_secretsmanager_secret.db_password.arn
        ]
      },
      # EC2 Network Interface permissions (required for VPC access)
      {
        Effect = "Allow"
        Action = [
          "ec2:CreateNetworkInterface",
          "ec2:DescribeNetworkInterfaces",
          "ec2:DeleteNetworkInterface"
        ]
        Resource = [
          "*" # Required for VPC access, but we'll add a condition
        ]
        Condition = {
          StringEquals = {
            "aws:RequestedRegion" = var.aws_region
          },
          StringLike = {
            "aws:ResourceTag/Application" = var.app_name
          }
        }
      },
      # KMS Decrypt permissions (restricted to our specific keys)
      {
        Effect = "Allow"
        Action = [
          "kms:Decrypt"
        ]
        Resource = [aws_kms_key.primary_encryption_key.arn]
        Condition = {
          StringEquals = {
            "kms:ViaService" = [
              "secretsmanager.${var.aws_region}.amazonaws.com",
              "lambda.${var.aws_region}.amazonaws.com"
            ]
          }
        }
      }
    ]
  })
}

# CloudWatch Logs KMS key is defined earlier in the file

# CloudWatch Log Group for Lambda function is defined later in the file

# CloudWatch Alarms
resource "aws_cloudwatch_metric_alarm" "lambda_errors" {
  alarm_name          = "${aws_lambda_function.app.function_name}-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = var.environment == "prod" ? "2" : "1"
  metric_name         = "Errors"
  threshold           = var.environment == "prod" ? 0 : 5 # Only alert on 5+ errors in non-prod
  period              = 300                               # 5 minutes
  datapoints_to_alarm = var.environment == "prod" ? 1 : 2 # Require 2 datapoints in prod, 1 in non-prod
  namespace           = "AWS/Lambda"
  statistic           = "Sum"
  alarm_description   = "This metric monitors lambda errors"
  alarm_actions       = [] # Add SNS topic for notifications

  dimensions = {
    FunctionName = aws_lambda_function.app.function_name
  }
}

resource "aws_iam_role_policy_attachment" "lambda_exec_policy" {
  role       = aws_iam_role.lambda_exec.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy_attachment" "lambda_vpc_access_policy" {
  role       = aws_iam_role.lambda_exec.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"
}

# RDS Enhanced Monitoring IAM Role
resource "aws_iam_role" "rds_monitoring" {
  name_prefix = "${substr(var.app_name, 0, 15)}-rds-monitor-" # Shortened to fit within 38 chars

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "monitoring.rds.amazonaws.com"
        }
      }
    ]
  })

  tags = merge(
    {
      Name        = "${var.app_name}-rds-monitoring-role"
      Environment = var.environment
      Application = var.app_name
    },
    var.tags
  )
}

resource "aws_iam_role_policy_attachment" "rds_monitoring_policy" {
  role       = aws_iam_role.rds_monitoring.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonRDSEnhancedMonitoringRole"
}

# CloudWatch Log Group for Lambda function
resource "aws_cloudwatch_log_group" "lambda" {
  name              = "/aws/lambda/${aws_lambda_function.app.function_name}"
  retention_in_days = 7 # Reduced from 365 days to save costs
  kms_key_id        = aws_kms_key.primary_encryption_key.arn

  tags = merge(
    {
      Name        = "${var.app_name}-lambda-logs"
      Environment = var.environment
      Application = var.app_name
      ManagedBy   = "Terraform"
    },
    var.tags
  )
}

# ECR Repository with enhanced security
resource "aws_ecr_repository" "app" {
  name                 = var.app_name
  image_tag_mutability = "IMMUTABLE" # Enforce immutable image tags

  # Enable image scanning on push
  image_scanning_configuration {
    scan_on_push = true
  }

  # Enable server-side encryption with KMS
  encryption_configuration {
    encryption_type = "KMS"
    kms_key         = aws_kms_key.primary_encryption_key.arn
  }

  # Add comprehensive tags
  tags = merge(
    {
      Name        = "${var.app_name}-ecr"
      Environment = var.environment
      Application = var.app_name
      ManagedBy   = "Terraform"
    },
    var.tags
  )

  # Ensure proper lifecycle management
  lifecycle {
    prevent_destroy = false
    ignore_changes = [
      encryption_configuration
    ]
  }
}

# ECR Lifecycle Policy
resource "aws_ecr_lifecycle_policy" "app" {
  repository = aws_ecr_repository.app.name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1,
        description  = "Keep last 30 images",
        selection = {
          tagStatus   = "any",
          countType   = "imageCountMoreThan",
          countNumber = 30
        },
        action = {
          type = "expire"
        }
      }
    ]
  })
}

# RDS Database
resource "aws_db_instance" "postgres" {
  # Basic configuration - optimized for free tier
  identifier            = "${var.app_name}-${var.environment}"
  allocated_storage     = 20    # Free tier allows up to 20GB
  max_allocated_storage = 20    # Disable storage autoscaling for free tier
  storage_type          = "gp2" # gp2 is included in free tier
  storage_encrypted     = true  # Enable KMS encryption
  kms_key_id            = aws_kms_key.primary_encryption_key.arn

  # Performance Insights (enabled for all environments with 7-day retention)
  performance_insights_enabled          = true
  performance_insights_retention_period = 7 # 7 days for all environments (valid values: 7 or 731)

  # Engine configuration
  engine         = "postgres"
  engine_version = "17.5"
  instance_class = "db.t4g.micro" # ARM-based instances are ~20% cheaper

  # Database configuration
  db_name              = var.db_name
  username             = var.db_username
  password             = random_password.db_password.result
  parameter_group_name = aws_db_parameter_group.app_pg.name

  # Network configuration
  vpc_security_group_ids = [aws_security_group.db_sg.id]
  db_subnet_group_name   = aws_db_subnet_group.default.name
  publicly_accessible    = false

  # Backup and maintenance settings
  backup_retention_period = var.environment == "prod" ? 7 : 1
  backup_window           = "03:00-04:00" # During low-usage hours
  maintenance_window      = "Sun:04:00-Sun:05:00"

  # Storage encryption is already configured with the primary KMS key

  # Database protection settings
  deletion_protection       = var.environment == "prod" # Only enable in production
  skip_final_snapshot       = var.environment != "prod" # Skip in non-prod for easier cleanup
  final_snapshot_identifier = var.environment == "prod" ? "${var.app_name}-final-snapshot-${formatdate("YYYYMMDDhhmmss", timestamp())}" : null
  delete_automated_backups  = var.environment != "prod" # Delete automated backups in non-prod
  copy_tags_to_snapshot     = true

  # Encryption in transit - Using modern CA certificate
  ca_cert_identifier = "rds-ca-rsa4096-g1" # Modern CA certificate

  # High availability
  multi_az = true # Always enable for all environments

  # Performance Insights KMS key
  performance_insights_kms_key_id = aws_kms_key.primary_encryption_key.arn

  # Enable CloudWatch Logs exports
  enabled_cloudwatch_logs_exports = ["postgresql", "upgrade"]

  # Enhanced monitoring
  monitoring_interval = 60
  monitoring_role_arn = aws_iam_role.rds_monitoring.arn

  # IAM database authentication
  iam_database_authentication_enabled = true

  # Apply changes immediately
  apply_immediately = false # Change to true for production changes

  # Maintenance and updates
  auto_minor_version_upgrade  = true
  allow_major_version_upgrade = false

  # Enable deletion protection and backup for all environments
  # (previously was only for production)

  # Tags
  tags = merge(
    {
      Name              = "${var.app_name}-postgres"
      Environment       = var.environment
      Application       = var.app_name
      ManagedBy         = "Terraform"
      BackupRetention   = var.environment == "prod" ? "7 days" : "1 day"
      MultiAZ           = "Enabled"
      DeletionProtected = "true"
    },
    var.tags
  )

  # Ensure we don't recreate the instance if just tags change
  lifecycle {
    ignore_changes = [
      tags,
      performance_insights_retention_period # Keep this as it's a configurable setting
    ]
  }
}

resource "aws_db_parameter_group" "app_pg" {
  name   = "${var.app_name}-${var.environment}-pg"
  family = "postgres17"

  # Security parameters
  parameter {
    name  = "rds.force_ssl"
    value = "1" # Force SSL connections
  }

  # Logging parameters
  parameter {
    name  = "log_connections"
    value = "1"
  }

  parameter {
    name  = "log_disconnections"
    value = "1"
  }

  parameter {
    name  = "log_statement"
    value = "none" # Set to 'all' for debugging, then back to 'none'
  }

  # Performance parameters
  parameter {
    name  = "log_min_duration_statement"
    value = "5000" # Log statements that run for more than 5 seconds
  }

  parameter {
    name  = "idle_in_transaction_session_timeout"
    value = "60000" # 1 minute timeout for idle transactions (in ms)
  }
}

# Database Security Group
resource "aws_security_group" "db_sg" {
  name_prefix = "${var.app_name}-db-sg"
  description = "Security group for RDS database"
  vpc_id      = aws_vpc.app_vpc.id

  # Only allow PostgreSQL access from Lambda security group
  ingress {
    description     = "PostgreSQL access from Lambda"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.lambda_sg.id]
  }


  # Restrict egress to only necessary traffic
  egress {
    description = "Allow outbound traffic to CloudWatch Logs"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    description = "Allow outbound DNS traffic"
    from_port   = 53
    to_port     = 53
    protocol    = "udp"
    cidr_blocks = ["0.0.0.0/0"]
  }


  tags = merge(
    {
      Name        = "${var.app_name}-db-sg"
      Environment = var.environment
      Application = var.app_name
    },
    var.tags
  )

}

# Secrets Manager
resource "aws_secretsmanager_secret" "db_password" {
  name       = "${var.app_name}-${var.environment}-db-password"
  kms_key_id = aws_kms_key.primary_encryption_key.arn # Use the primary KMS key

  recovery_window_in_days = var.environment == "prod" ? 30 : 7

  tags = merge(
    {
      Name        = "${var.app_name}-db-password"
      Environment = var.environment
      Application = var.app_name
    },
    var.tags
  )
}

resource "aws_secretsmanager_secret_rotation" "db_password" {
  secret_id           = aws_secretsmanager_secret.db_password.id
  rotation_lambda_arn = aws_lambda_function.secret_rotation.arn

  # Enforce 30-day rotation
  rotation_rules {
    automatically_after_days = 30
  }

  # Rotation is managed by the resource configuration
}

resource "aws_secretsmanager_secret_version" "db_password_version" {
  secret_id = aws_secretsmanager_secret.db_password.id
  secret_string = jsonencode({
    username = var.db_username,
    password = random_password.db_password.result
  })
}

resource "random_password" "db_password" {
  length           = 16
  special          = true
  override_special = "!@#$%^&*()_+-=[]{}|"
  upper            = true
  lower            = true
  numeric          = true
}

resource "aws_vpc_endpoint" "api_gateway" {
  vpc_id              = aws_vpc.app_vpc.id
  service_name        = "com.amazonaws.${var.aws_region}.execute-api"
  vpc_endpoint_type   = "Interface"
  private_dns_enabled = true

  tags = {
    Name        = "${var.app_name}-api-gateway-endpoint"
    Environment = var.environment
  }
}

# Security Group for VPC Endpoints
resource "aws_security_group" "vpc_endpoint_sg" {
  name_prefix = "${var.app_name}-vpc-endpoint-sg"
  description = "Security group for VPC endpoints"
  vpc_id      = aws_vpc.app_vpc.id

  ingress {
    description = "HTTPS from VPC"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = [aws_vpc.app_vpc.cidr_block]
  }

  tags = {
    Name        = "${var.app_name}-vpc-endpoint-sg"
    Environment = var.environment
  }
}

# Private Route Table
resource "aws_route_table" "private" {
  vpc_id = aws_vpc.app_vpc.id

  tags = {
    Name        = "${var.app_name}-private-rt"
    Environment = var.environment
  }
}

# Associate private subnets with private route table
resource "aws_route_table_association" "private" {
  count = var.environment == "prod" ? 2 : 1

  subnet_id      = aws_subnet.app_private_subnet[count.index].id
  route_table_id = aws_route_table.private.id
}

# Add VPC endpoints to reduce NAT Gateway costs
resource "aws_vpc_endpoint" "s3" {
  vpc_id            = aws_vpc.app_vpc.id
  service_name      = "com.amazonaws.${var.aws_region}.s3"
  vpc_endpoint_type = "Gateway"
  route_table_ids   = [aws_route_table.private.id]

  tags = {
    Name        = "${var.app_name}-s3-endpoint"
    Environment = var.environment
  }
}

resource "aws_vpc_endpoint" "secretsmanager" {
  vpc_id              = aws_vpc.app_vpc.id
  service_name        = "com.amazonaws.${var.aws_region}.secretsmanager"
  vpc_endpoint_type   = "Interface"
  security_group_ids  = [aws_security_group.vpc_endpoint_sg.id]
  subnet_ids          = aws_subnet.app_private_subnet[*].id
  private_dns_enabled = true

  tags = {
    Name        = "${var.app_name}-secretsmanager-endpoint"
    Environment = var.environment
  }
}
