# Default AWS provider configuration for the primary region
provider "aws" {
  region = var.aws_region

  # Assume role if provided, otherwise use default credentials
  dynamic "assume_role" {
    for_each = var.assume_role_arn != "" ? [1] : []

    content {
      role_arn = var.assume_role_arn
    }
  }

}

# AWS provider alias for us-east-1 (required for ACM certificates used by API Gateway)
provider "aws" {
  alias  = "us-east-1"
  region = "us-east-1"

  # Assume role if provided, otherwise use default credentials
  dynamic "assume_role" {
    for_each = var.assume_role_arn != "" ? [1] : []

    content {
      role_arn = var.assume_role_arn
    }
  }

}
