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
  # Main cert covers: *.<env>.<base_domain> (covers meals.<env>.<base_domain>)
  main_cert_domain = var.environment == "prod" ? "*.${var.base_domain}" : "*.${var.environment}.${var.base_domain}"
  # API cert covers: *.<app_subdomain>.<env>.<base_domain> (covers api.<app_subdomain>.<env>.<base_domain>)
  api_cert_domain = var.environment == "prod" ? "*.${var.app_subdomain}.${var.base_domain}" : "*.${var.app_subdomain}.${var.environment}.${var.base_domain}"

  # API domain name based on environment
  app_domain_name = var.environment == "prod" ? "${var.app_subdomain}.${var.base_domain}" : "${var.app_subdomain}.${var.environment}.${var.base_domain}"

  # API domain prefix for constructing API Gateway domain
  api_domain_prefix = var.api_domain_prefix != null ? var.api_domain_prefix : "api"

  # API Gateway domain name: api.meals.dev.nivecher.com
  # This matches what we set in the API Gateway module
  api_gateway_domain_name = "api.${local.app_domain_name}"

  # Set budget amount based on environment
  budget_amount = var.environment == "prod" ? "20.0" : "5.0"

  # Use provided monthly_budget_amount or default to environment-based amount
  monthly_budget = coalesce(var.monthly_budget_amount, local.budget_amount)

  # CORS origins for API Gateway
  # These are the domains that browsers will send as the 'Origin' header
  base_cors_origins = [
    "https://${local.app_domain_name}", # Main application domain (via CloudFront)
    "http://localhost:5000",            # Local development
    "https://localhost:5000"            # Local development with HTTPS
  ]
}
