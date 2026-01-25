# staging environment configuration
environment = "staging"
aws_region  = "us-east-1"
app_name    = "meal-expense-tracker"

# Cost control
monthly_budget_amount = 20

# Add any additional environment-specific variables below
# Increased from 5 to 15 to prevent throttling during concurrent requests and testing
lambda_reserved_concurrency = 15
