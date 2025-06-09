provider "aws" {
  region = var.aws_region

  default_tags {
    tags = merge(
      {
        Environment = var.environment
        Application = var.app_name
        ManagedBy   = "Terraform"
      },
      var.tags
    )
  }
}

provider "random" {}

# Get current AWS account and region
data "aws_caller_identity" "current" {}
data "aws_region" "current" {}
data "aws_availability_zones" "available" {}
