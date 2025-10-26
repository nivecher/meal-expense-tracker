locals {
  # Standardized name prefix for all resources
  name = "${var.app_name}-${var.environment}"

  # Standardized name prefix with region (useful for global resources)
  name_with_region = "${var.app_name}-${var.environment}-${var.aws_region}"

  # Standardized name prefix with account ID
  name_with_account = "${var.app_name}-${var.environment}-${data.aws_caller_identity.current.account_id}"

  # Standard tags according to https://www.terraform-best-practices.com/naming
  tags = merge(
    {
      "Name"        = local.name
      "Environment" = var.environment
      "ManagedBy"   = "terraform"
      "Project"     = var.app_name
      "Owner"       = var.owner
    },
    coalesce(var.tags, {})
  )

  # Domain names configuration
  domain_name = var.environment == "prod" ? var.base_domain : "${var.environment}.${var.base_domain}"

  # Certificate domain (wildcard for subdomains)
  cert_domain = var.environment == "prod" ? "*.${var.base_domain}" : "*.${var.environment}.${var.base_domain}"

  # API domain name based on environment
  api_domain_name = var.environment == "prod" ? "${var.api_subdomain}.${var.base_domain}" : "${var.api_subdomain}.${var.environment}.${var.base_domain}"

  # Set budget amount based on environment
  budget_amount = var.environment == "prod" ? "20.0" : "5.0"

  # Use provided monthly_budget_amount or default to environment-based amount
  monthly_budget = coalesce(var.monthly_budget_amount, local.budget_amount)
}
