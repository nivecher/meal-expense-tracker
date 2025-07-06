# prod environment configuration
environment = "prod"
aws_region = "us-east-1"
app_name   = "meal-expense-tracker"

# Database configuration
db_instance_class      = "db.t3.medium"
db_allocated_storage   = 100

# Feature flags
enable_cloudwatch_logs = true
enable_xray_tracing    = true

# Cost control
enable_cost_alert    = true
monthly_budget_amount = 500

# Security
allowed_ip_ranges = ["0.0.0.0/0"]  # Restrict this in production

# Add any additional environment-specific variables below

