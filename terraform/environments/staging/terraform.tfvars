# staging environment configuration
environment = "staging"
aws_region  = "us-east-1"
app_name    = "meal-expense-tracker"

# Database configuration
db_instance_class    = "db.t3.micro"
db_allocated_storage = 50

# Feature flags
enable_cloudwatch_logs = true
enable_xray_tracing    = false

# Cost control
enable_cost_alert     = true
monthly_budget_amount = 200

# Security
allowed_ip_ranges = ["0.0.0.0/0"] # Restrict this in production

# Add any additional environment-specific variables below
