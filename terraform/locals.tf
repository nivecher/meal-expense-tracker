# Common tags to be used for all resources
locals {
  # Common tags for all resources
  common_tags = merge({
    Environment = var.environment
    Application = var.app_name
    ManagedBy   = "Terraform"
  }, var.tags)

}
