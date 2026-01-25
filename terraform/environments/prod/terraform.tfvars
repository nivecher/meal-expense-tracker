# prod environment configuration
environment = "prod"
aws_region  = "us-east-1"
app_name    = "meal-expense-tracker"

# Cost control
monthly_budget_amount = 50

# Add any additional environment-specific variables below
# Increased from 10 to 25 to handle production load and prevent throttling
lambda_reserved_concurrency = 25
