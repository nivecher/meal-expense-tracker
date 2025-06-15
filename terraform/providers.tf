# Default AWS provider
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

# Provider for ACM certificates in us-east-1 (required for API Gateway custom domains)
provider "aws" {
  alias  = "us-east-1"
  region = "us-east-1"

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
