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

data "aws_caller_identity" "current" {}

locals {
  account_id = data.aws_caller_identity.current.account_id
}

data "aws_availability_zones" "available" {}

# VPC for the application
resource "aws_vpc" "app_vpc" {
  cidr_block = "10.0.0.0/16"

  enable_dns_support   = true
  enable_dns_hostnames = true

  tags = {
    Name        = "${var.app_name}-vpc"
    Environment = var.environment
  }
}

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

resource "aws_route_table" "app_private_route_table" {
  vpc_id = aws_vpc.app_vpc.id

  # No default route to 0.0.0.0/0 via VPC endpoint, as this is not supported.
  # Add a NAT Gateway or Internet Gateway route here if outbound internet access is required.

  tags = {
    Name        = "${var.app_name}-private-route-table"
    Environment = var.environment
  }
}

resource "aws_route_table_association" "app_private_route_table_association" {
  count          = 2
  subnet_id      = aws_subnet.app_private_subnet[count.index].id
  route_table_id = aws_route_table.app_private_route_table.id
}

# Lambda function using Docker image from ECR
resource "aws_lambda_function" "app" {
  function_name = "${var.app_name}-${var.environment}"
  role          = aws_iam_role.lambda_exec.arn
  package_type  = "Image"
  image_uri     = "${aws_ecr_repository.app.repository_url}:${var.image_tag}"
  timeout       = 30
  memory_size   = 512

  environment {
    variables = {
      DATABASE_URL           = "postgresql://${jsondecode(aws_secretsmanager_secret_version.db_password_version.secret_string).username}:${jsondecode(aws_secretsmanager_secret_version.db_password_version.secret_string).password}@${aws_db_instance.postgres.endpoint}/${var.db_name}"
      DB_SECRET_ARN          = aws_secretsmanager_secret.db_password.arn
      API_GATEWAY_HTTPS_ONLY = "true"
    }
  }

  vpc_config {
    subnet_ids         = aws_subnet.app_private_subnet[*].id
    security_group_ids = [aws_security_group.lambda_sg.id]
  }
}

# API Gateway to expose Lambda function
resource "aws_apigatewayv2_api" "http_api" {
  name          = "${var.app_name}-${var.environment}"
  protocol_type = "HTTP"
}

resource "aws_apigatewayv2_integration" "lambda" {
  api_id                 = aws_apigatewayv2_api.http_api.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.app.invoke_arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "default" {
  api_id    = aws_apigatewayv2_api.http_api.id
  route_key = "$default"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
}

resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.http_api.id
  name        = "$default"
  auto_deploy = true
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
}

resource "aws_iam_role_policy_attachment" "lambda_exec_policy" {
  role       = aws_iam_role.lambda_exec.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy_attachment" "lambda_vpc_access_policy" {
  role       = aws_iam_role.lambda_exec.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"
}

# ECR Repository
resource "aws_ecr_repository" "app" {
  name = var.app_name

  lifecycle {
    prevent_destroy = true
  }
}

resource "aws_acm_certificate" "app" {
  domain_name       = var.domain_name
  validation_method = "DNS"

  tags = {
    Environment = var.environment
    Application = var.app_name
  }
}

resource "aws_db_instance" "postgres" {
  allocated_storage      = 20
  engine                 = "postgres"
  engine_version         = "17.5"
  instance_class         = "db.t3.micro"
  username               = var.db_username
  password               = random_password.db_password.result
  vpc_security_group_ids = [aws_security_group.db_sg.id]
  db_subnet_group_name   = aws_db_subnet_group.default.name
  publicly_accessible    = false
  skip_final_snapshot    = true
  storage_encrypted      = true
  kms_key_id             = aws_kms_key.db_encryption_key.arn

  tags = {
    Environment = var.environment
    Application = var.app_name
  }
}

resource "aws_kms_key" "db_encryption_key" {
  description = "KMS key for encrypting RDS database."

  tags = {
    Name        = "${var.app_name}-db-encryption-key"
    Environment = var.environment
  }
}

resource "aws_kms_alias" "db_encryption_alias" {
  name          = "alias/${var.app_name}-db-encryption-key"
  target_key_id = aws_kms_key.db_encryption_key.id
}

resource "aws_security_group" "db_sg" {
  vpc_id = aws_vpc.app_vpc.id

  ingress {
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"
    cidr_blocks = ["10.0.0.0/16"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "${var.app_name}-db-sg"
    Environment = var.environment
  }
}

resource "aws_db_subnet_group" "default" {
  name       = "${var.app_name}-db-subnet-group"
  subnet_ids = aws_subnet.app_private_subnet[*].id

  tags = {
    Name        = "${var.app_name}-db-subnet-group"
    Environment = var.environment
  }
}

resource "aws_secretsmanager_secret" "db_password" {
  name = "${var.app_name}-${var.environment}-db-password"

  tags = {
    Environment = var.environment
    Application = var.app_name
  }
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

resource "aws_security_group" "lambda_sg" {
  vpc_id = aws_vpc.app_vpc.id

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["10.0.0.0/16"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "${var.app_name}-lambda-sg"
    Environment = var.environment
  }
}