# dev environment configuration
environment = "dev"
aws_region  = "us-east-1"
app_name    = "meal-expense-tracker"

# Domain configuration
base_domain   = "nivecher.com"
api_subdomain = "meals"

# Lambda configuration for Docker deployment
lambda_architecture = "arm64"
lambda_memory_size  = 1024
lambda_timeout      = 60

# Database configuration
run_migrations = true
log_level      = "INFO"

# Cost control
monthly_budget_amount = 10
