# Main configuration for dev environment

# Include common configuration
module "common" {
  source = "../.."

  # Pass variables from this environment's terraform.tfvars
  environment = var.environment
  aws_region  = var.aws_region
  app_name    = var.app_name

  # Pass through other variables
  tags = var.common_tags
}

# Import any environment-specific modules here
# Example:
# module "dev_specific" {
#   source = "../../modules/dev_specific"
#
#   # Pass required variables
#   vpc_id = module.common.vpc_id
#   ...
# }

# Add any additional environment-specific outputs here
