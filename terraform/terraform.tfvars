aws_region  = "us-east-1"
environment = "prod"
app_name    = "meal-expense-tracker"

# Using SQLite for initial deployment
database_url = "sqlite:////app/instance/meal_expenses.db"
#secret_key   = "dev-secret-key-replace-in-production"

image_tag = "latest"
