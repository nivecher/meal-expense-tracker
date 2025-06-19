# Backend configuration for Terraform state management
# This file is a placeholder that will be overridden by the -backend-config flag
# in the Makefile for different environments.
# The actual backend configuration is stored in environments/<env>/backend.hcl

terraform {
  # This empty backend block is a placeholder that will be overridden
  # by the -backend-config flag passed during terraform init
  backend "s3" {
    # All configuration is provided via backend.hcl in each environment directory
  }
}

# Note: The actual backend configuration is managed via the -backend-config
# flag in the Makefile, which points to the appropriate environment's
# backend.hcl file. This allows for different backend configurations
# for different environments (dev, staging, prod) while keeping sensitive
# information out of version control.
