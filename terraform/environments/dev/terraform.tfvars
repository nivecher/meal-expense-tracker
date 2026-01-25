# dev environment configuration
environment = "dev"
aws_region  = "us-east-1"
app_name    = "meal-expense-tracker"

# Domain configuration
base_domain   = "nivecher.com"
app_subdomain = "meals"

# Lambda configuration for Docker deployment
# Using x86_64 for faster local builds (native architecture)
# Can switch to arm64 for production to save ~20% on runtime costs
lambda_architecture = "x86_64"
lambda_memory_size  = 1024
lambda_timeout      = 300
# Increased from 2 to 10 to prevent throttling during concurrent requests
# With 2, any 3+ simultaneous requests would throttle
lambda_reserved_concurrency = 10

# Database configuration
run_migrations = false
log_level      = "INFO"

# Cost control
monthly_budget_amount = 10
