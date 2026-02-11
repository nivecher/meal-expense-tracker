# staging environment configuration
environment = "staging"
aws_region  = "us-east-1"
app_name    = "meal-expense-tracker"

# Domain configuration
base_domain   = "nivecher.com"
app_subdomain = "meals"

lambda_architecture = "x86_64"
lambda_memory_size  = 1024
lambda_timeout      = 300

# Add any additional environment-specific variables below
# Increased from 5 to 15 to prevent throttling during concurrent requests and testing
lambda_reserved_concurrency = 15

# Cost control
monthly_budget_amount = 20
