# VPC
resource "aws_vpc" "main" {
  cidr_block           = var.vpc_cidr
  enable_dns_support   = true
  enable_dns_hostnames = true

  tags = merge({
    Name = "${var.app_name}-${var.environment}-vpc"
  }, var.tags)
}

# VPC Flow Logs Resources
# Note: These resources are conditionally created based on the enable_flow_logs variable
resource "aws_cloudwatch_log_group" "vpc_flow_logs" {
  count             = var.enable_flow_logs ? 1 : 0
  name              = "/aws/vpc-flow-logs/${var.app_name}-${var.environment}"
  retention_in_days = var.flow_logs_retention_in_days
  kms_key_id        = var.logs_kms_key_arn

  tags = merge({
    Name = "${var.app_name}-${var.environment}-vpc-flow-logs"
  }, var.tags)
}

# IAM Role for VPC Flow Logs
resource "aws_iam_role" "vpc_flow_logs_role" {
  count = var.enable_flow_logs ? 1 : 0
  name  = "${var.app_name}-${var.environment}-vpc-flow-logs-role"

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

  tags = merge({
    Name = "${var.app_name}-${var.environment}-vpc-flow-logs-role"
  }, var.tags)
}

# IAM Policy for VPC Flow Logs
resource "aws_iam_role_policy" "vpc_flow_logs_policy" {
  count = var.enable_flow_logs ? 1 : 0
  name  = "${var.app_name}-${var.environment}-vpc-flow-logs-policy"
  role  = aws_iam_role.vpc_flow_logs_role[0].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents",
          "logs:DescribeLogGroups",
          "logs:DescribeLogStreams"
        ]
        Resource = [
          "arn:aws:logs:${var.region}:${data.aws_caller_identity.current.account_id}:log-group:/aws/vpc-flow-logs/*",
          "arn:aws:logs:${var.region}:${data.aws_caller_identity.current.account_id}:log-group:/aws/vpc-flow-logs/*:*"
        ]
      }
    ]
  })
}

# VPC Flow Logs
resource "aws_flow_log" "vpc_flow_logs" {
  count                = var.enable_flow_logs ? 1 : 0
  log_destination      = aws_cloudwatch_log_group.vpc_flow_logs[0].arn
  log_destination_type = "cloud-watch-logs"
  traffic_type         = "ALL"
  vpc_id               = aws_vpc.main.id
  iam_role_arn         = aws_iam_role.vpc_flow_logs_role[0].arn

  tags = merge({
    Name = "${var.app_name}-${var.environment}-vpc-flow-logs"
  }, var.tags)
}

# Public Subnets
resource "aws_subnet" "public" {
  count             = 3
  vpc_id            = aws_vpc.main.id
  cidr_block        = cidrsubnet(var.vpc_cidr, 8, count.index)
  availability_zone = data.aws_availability_zones.available.names[count.index]

  tags = merge({
    Name                     = "${var.app_name}-${var.environment}-public-${count.index + 1}"
    "kubernetes.io/role/elb" = "1"
  }, var.tags)
}

# Private Subnets
resource "aws_subnet" "private" {
  count             = 3
  vpc_id            = aws_vpc.main.id
  cidr_block        = cidrsubnet(var.vpc_cidr, 8, count.index + 10)
  availability_zone = data.aws_availability_zones.available.names[count.index]

  tags = merge({
    Name                              = "${var.app_name}-${var.environment}-private-${count.index + 1}"
    "kubernetes.io/role/internal-elb" = "1"
  }, var.tags)
}

# Internet Gateway
resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id

  tags = merge({
    Name = "${var.app_name}-${var.environment}-igw"
  }, var.tags)
}

# NAT Gateway
resource "aws_eip" "nat" {
  domain = "vpc"

  tags = merge({
    Name = "${var.app_name}-${var.environment}-nat-eip"
  }, var.tags)
}

resource "aws_nat_gateway" "main" {
  allocation_id = aws_eip.nat.id
  subnet_id     = aws_subnet.public[0].id

  tags = merge({
    Name = "${var.app_name}-${var.environment}-nat"
  }, var.tags)

  depends_on = [aws_internet_gateway.main]
}

# Route Tables
resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main.id
  }

  tags = merge({
    Name = "${var.app_name}-${var.environment}-public-rt"
  }, var.tags)
}

resource "aws_route_table" "private" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.main.id
  }

  tags = merge({
    Name = "${var.app_name}-${var.environment}-private-rt"
  }, var.tags)
}

# Route Table Associations
resource "aws_route_table_association" "public" {
  count          = length(aws_subnet.public)
  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}

resource "aws_route_table_association" "private" {
  count          = length(aws_subnet.private)
  subnet_id      = aws_subnet.private[count.index].id
  route_table_id = aws_route_table.private.id
}

# Database Subnet Group
resource "aws_db_subnet_group" "main" {
  name       = "${var.app_name}-${var.environment}-db-subnet-group"
  subnet_ids = aws_subnet.private[*].id

  tags = merge({
    Name = "${var.app_name}-${var.environment}-db-subnet-group"
  }, var.tags)
}

# VPC Endpoints
resource "aws_vpc_endpoint" "s3" {
  vpc_id            = aws_vpc.main.id
  service_name      = "com.amazonaws.${var.region}.s3"
  vpc_endpoint_type = "Gateway"

  # Since we only have one private route table, we can reference it directly
  # If you have multiple private route tables, you can use a for_each or count
  route_table_ids = [aws_route_table.private.id]

  tags = merge({
    Name = "${var.app_name}-${var.environment}-s3-endpoint"
  }, var.tags)
}

resource "aws_vpc_endpoint" "ecr_api" {
  vpc_id              = aws_vpc.main.id
  service_name        = "com.amazonaws.${var.region}.ecr.api"
  vpc_endpoint_type   = "Interface"
  private_dns_enabled = true
  subnet_ids          = aws_subnet.private[*].id
  security_group_ids  = [aws_security_group.vpc_endpoints.id]

  tags = merge({
    Name = "${var.app_name}-${var.environment}-ecr-api-endpoint"
  }, var.tags)
}

resource "aws_vpc_endpoint" "ecr_dkr" {
  vpc_id              = aws_vpc.main.id
  service_name        = "com.amazonaws.${var.region}.ecr.dkr"
  vpc_endpoint_type   = "Interface"
  private_dns_enabled = true
  subnet_ids          = aws_subnet.private[*].id
  security_group_ids  = [aws_security_group.vpc_endpoints.id]

  tags = merge({
    Name = "${var.app_name}-${var.environment}-ecr-dkr-endpoint"
  }, var.tags)
}

resource "aws_vpc_endpoint" "logs" {
  vpc_id              = aws_vpc.main.id
  service_name        = "com.amazonaws.${var.region}.logs"
  vpc_endpoint_type   = "Interface"
  private_dns_enabled = true
  subnet_ids          = aws_subnet.private[*].id
  security_group_ids  = [aws_security_group.vpc_endpoints.id]

  tags = merge({
    Name = "${var.app_name}-${var.environment}-logs-endpoint"
  }, var.tags)
}

resource "aws_vpc_endpoint" "secretsmanager" {
  vpc_id              = aws_vpc.main.id
  service_name        = "com.amazonaws.${var.region}.secretsmanager"
  vpc_endpoint_type   = "Interface"
  private_dns_enabled = true
  subnet_ids          = aws_subnet.private[*].id
  security_group_ids  = [aws_security_group.vpc_endpoints.id]

  tags = merge({
    Name = "${var.app_name}-${var.environment}-secretsmanager-endpoint"
  }, var.tags)
}

resource "aws_vpc_endpoint" "ssm" {
  vpc_id              = aws_vpc.main.id
  service_name        = "com.amazonaws.${var.region}.ssm"
  vpc_endpoint_type   = "Interface"
  private_dns_enabled = true
  subnet_ids          = aws_subnet.private[*].id
  security_group_ids  = [aws_security_group.vpc_endpoints.id]

  tags = merge({
    Name = "${var.app_name}-${var.environment}-ssm-endpoint"
  }, var.tags)
}

resource "aws_vpc_endpoint" "ssmmessages" {
  vpc_id              = aws_vpc.main.id
  service_name        = "com.amazonaws.${var.region}.ssmmessages"
  vpc_endpoint_type   = "Interface"
  private_dns_enabled = true
  subnet_ids          = aws_subnet.private[*].id
  security_group_ids  = [aws_security_group.vpc_endpoints.id]

  tags = merge({
    Name = "${var.app_name}-${var.environment}-ssmmessages-endpoint"
  }, var.tags)
}

resource "aws_vpc_endpoint" "kms" {
  vpc_id              = aws_vpc.main.id
  service_name        = "com.amazonaws.${var.region}.kms"
  vpc_endpoint_type   = "Interface"
  private_dns_enabled = true
  subnet_ids          = aws_subnet.private[*].id
  security_group_ids  = [aws_security_group.vpc_endpoints.id]

  tags = merge({
    Name = "${var.app_name}-${var.environment}-kms-endpoint"
  }, var.tags)
}

# Security group for VPC endpoints
resource "aws_security_group" "vpc_endpoints" {
  name        = "${var.app_name}-${var.environment}-vpc-endpoints-sg"
  description = "Security group for VPC endpoints"
  vpc_id      = aws_vpc.main.id

  # Allow HTTPS from VPC CIDR
  ingress {
    description = "Allow HTTPS from VPC"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = [var.vpc_cidr]
  }


  tags = merge({
    Name = "${var.app_name}-${var.environment}-vpc-endpoints-sg"
  }, var.tags)
}

# Security Groups
resource "aws_security_group" "lambda" {
  name        = "${var.app_name}-${var.environment}-lambda-sg"
  description = "Security group for Lambda functions"
  vpc_id      = aws_vpc.main.id

  # No ingress rules needed for Lambda functions
  # as they are invoked via AWS services, not direct inbound traffic

  # Restrict egress to only necessary AWS services via VPC endpoints
  # Allow outbound to all VPC endpoints
  egress {
    description = "Allow outbound to all VPC endpoints"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = [aws_vpc.main.cidr_block]
  }

  # Allow outbound to S3 VPC endpoint
  egress {
    description     = "Allow outbound to S3 VPC endpoint"
    from_port       = 443
    to_port         = 443
    protocol        = "tcp"
    prefix_list_ids = [aws_vpc_endpoint.s3.prefix_list_id]
  }

  # Allow outbound DNS (UDP 53) for DNS resolution
  egress {
    description = "Allow outbound DNS"
    from_port   = 53
    to_port     = 53
    protocol    = "udp"
    cidr_blocks = [var.vpc_cidr] # Use the VPC's CIDR block for DNS resolution
  }

  # Allow outbound NTP (UDP 123) for time synchronization
  egress {
    description = "Allow outbound NTP"
    from_port   = 123
    to_port     = 123
    protocol    = "udp"
    cidr_blocks = ["169.254.169.123/32"] # Amazon Time Sync Service
  }

  tags = merge({
    Name = "${var.app_name}-${var.environment}-lambda-sg"
  }, var.tags)
}

resource "aws_security_group" "rds" {
  name        = "${var.app_name}-${var.environment}-rds-sg"
  description = "Security group for RDS PostgreSQL database"
  vpc_id      = aws_vpc.main.id

  # Ingress rule for PostgreSQL access from Lambda
  ingress {
    description     = "Allow PostgreSQL access from Lambda security group"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.lambda.id]
  }

  # Restrict egress traffic to only what's necessary
  # Allow outbound to all VPC endpoints
  egress {
    description = "Allow outbound to all VPC endpoints"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = [aws_vpc.main.cidr_block]
  }

  # Allow outbound to S3 VPC endpoint
  egress {
    description     = "Allow outbound to S3 VPC endpoint"
    from_port       = 443
    to_port         = 443
    protocol        = "tcp"
    prefix_list_ids = [aws_vpc_endpoint.s3.prefix_list_id]
  }

  # Allow outbound DNS (UDP 53) for DNS resolution
  egress {
    description = "Allow outbound DNS"
    from_port   = 53
    to_port     = 53
    protocol    = "udp"
    cidr_blocks = [var.vpc_cidr] # Use the VPC's CIDR block for DNS resolution
  }

  # Allow outbound NTP (UDP 123) for time synchronization
  egress {
    description = "Allow outbound NTP"
    from_port   = 123
    to_port     = 123
    protocol    = "udp"
    cidr_blocks = ["169.254.169.123/32"] # Amazon Time Sync Service
  }

  # Note: In AWS Security Groups, all traffic is denied by default.
  # Only explicitly allowed egress rules are permitted.
  # No need to explicitly deny traffic in AWS Security Groups.

  # Add tags for better resource management
  tags = merge({
    Name        = "${var.app_name}-${var.environment}-rds-sg"
    Environment = var.environment
    ManagedBy   = "terraform"
    CostCenter  = var.app_name
  }, var.tags)
}

# Data Sources
data "aws_caller_identity" "current" {}

data "aws_availability_zones" "available" {
  state = "available"
}

# Outputs
output "vpc_id" {
  description = "The ID of the VPC"
  value       = aws_vpc.main.id
}

output "public_subnet_ids" {
  description = "List of public subnet IDs"
  value       = aws_subnet.public[*].id
}

output "private_subnet_ids" {
  description = "List of private subnet IDs"
  value       = aws_subnet.private[*].id
}

output "db_subnet_group_name" {
  description = "Name of the DB subnet group"
  value       = aws_db_subnet_group.main.name
}

output "db_security_group_id" {
  description = "ID of the RDS security group"
  value       = aws_security_group.rds.id
}

output "lambda_security_group_id" {
  description = "ID of the Lambda security group"
  value       = aws_security_group.lambda.id
}
