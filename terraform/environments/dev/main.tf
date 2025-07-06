# Main configuration for dev environment

module "common" {
  source      = "../.."
  environment = var.environment
  aws_region  = var.aws_region
  app_name    = var.app_name
  vpc_cidr    = var.vpc_cidr
  tags        = var.tags
}

# Add any additional environment-specific modules or outputs here
