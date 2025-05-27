provider "aws" {
  region = var.aws_region
}

# VPC and Networking
module "vpc" {
  source = "./modules/vpc"
  
  environment = var.environment
  vpc_cidr    = var.vpc_cidr
}

# ECR Repository
module "ecr" {
  source = "./modules/ecr"
  
  repository_name = var.ecr_repository_name
  environment     = var.environment
}

# ECS Cluster and Service
module "ecs" {
  source = "./modules/ecs"
  
  environment           = var.environment
  vpc_id               = module.vpc.vpc_id
  public_subnet_ids    = module.vpc.public_subnet_ids
  private_subnet_ids   = module.vpc.private_subnet_ids
  ecr_repository_url   = module.ecr.repository_url
  app_port             = var.app_port
  app_count            = var.app_count
  task_cpu             = var.task_cpu
  task_memory          = var.task_memory
  google_maps_api_key  = var.google_maps_api_key
}

# RDS Database
module "rds" {
  source = "./modules/rds"
  
  environment         = var.environment
  vpc_id             = module.vpc.vpc_id
  private_subnet_ids = module.vpc.private_subnet_ids
  db_name            = var.db_name
  db_username        = var.db_username
  db_password        = var.db_password
}

# CloudWatch Logs
module "cloudwatch" {
  source = "./modules/cloudwatch"
  
  environment = var.environment
  app_name    = var.app_name
} 