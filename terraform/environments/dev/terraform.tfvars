# dev environment configuration
environment = "dev"
aws_region  = "us-east-1"
app_name    = "meal-expense-tracker"

# Domain configuration
base_domain   = "nivecher.com"
api_subdomain = "meals"

# Lambda configuration for Docker deployment
# Using x86_64 for faster local builds (native architecture)
# Can switch to arm64 for production to save ~20% on runtime costs
lambda_architecture = "x86_64"
lambda_memory_size  = 1024
lambda_timeout      = 60

# Database configuration
run_migrations = true
log_level      = "INFO"

# Cost control
monthly_budget_amount = 10
