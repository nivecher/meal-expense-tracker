#!/bin/bash
set -e

# Function to get instance type based on environment
get_instance_type() {
  local env=$1
  if [ "$env" = "prod" ]; then
    echo "t3.medium"
  elif [ "$env" = "staging" ]; then
    echo "t3.small"
  else
    echo "t3.micro"
  fi
}

# Function to get database instance class
get_db_instance_class() {
  local env=$1
  if [ "$env" = "prod" ]; then
    echo "db.t3.medium"
  else
    echo "db.t3.micro"
  fi
}

# Function to get database storage size
get_db_storage() {
  local env=$1
  if [ "$env" = "prod" ]; then
    echo 100
  elif [ "$env" = "staging" ]; then
    echo 50
  else
    echo 20
  fi
}

# Function to get scaling values
get_scaling_value() {
  local env=$1
  local type=$2

  case "$type" in
  min)
    [ "$env" = "prod" ] && echo 2 || echo 1
    ;;
  max)
    if [ "$env" = "prod" ]; then
      echo 6
    elif [ "$env" = "staging" ]; then
      echo 4
    else
      echo 2
    fi
    ;;
  desired)
    [ "$env" = "prod" ] && echo 3 || echo 1
    ;;
  esac
}

# Function to get monthly budget
get_monthly_budget() {
  local env=$1
  if [ "$env" = "prod" ]; then
    echo 500
  elif [ "$env" = "staging" ]; then
    echo 200
  else
    echo 50
  fi
}

# Create environment variable files for all environments
for env in dev staging prod; do
  cat >"terraform/environments/$env/terraform.tfvars" <<EOF
# $env environment configuration
environment = "$env"
aws_region = "us-east-1"
app_name   = "meal-expense-tracker"

# Database configuration
db_instance_class      = "$(get_db_instance_class $env)"
db_allocated_storage   = $(get_db_storage $env)

# Feature flags
enable_cloudwatch_logs = true
enable_xray_tracing    = $([ "$env" = "prod" ] && echo "true" || echo "false")

# Cost control
enable_cost_alert    = true
monthly_budget_amount = $(get_monthly_budget $env)

# Security
allowed_ip_ranges = ["0.0.0.0/0"]  # Restrict this in production

# Add any additional environment-specific variables below

EOF

  echo "Created configuration for $env environment"
done

printf "\nEnvironment configurations created successfully!\n"
printf "Review and customize the files in terraform/environments/\n"
