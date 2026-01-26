#!/usr/bin/env bash
# Run database migrations against Supabase
# This can be run from any machine with network access to Supabase

set -euo pipefail

show_usage() {
  cat <<'EOF'
Usage: ./scripts/run-supabase-migration.sh [options]

Options:
  -e, --env ENV            Target environment (dev|staging|prod). Default: dev
  -r, --region REGION      AWS region for Secrets Manager. Default: us-east-1
  -a, --app-name NAME      App name prefix for secrets. Default: meal-expense-tracker
      --secret-name NAME   Full Secrets Manager secret name override
  -h, --help               Show this help

Examples:
  ./scripts/run-supabase-migration.sh --env staging
  ./scripts/run-supabase-migration.sh --secret-name meal-expense-tracker/staging/supabase-connection
EOF
}

validate_environment() {
  local -r env="$1"
  case "$env" in
    dev|staging|prod)
      return 0
      ;;
    *)
      echo "❌ Invalid --env '$env'. Expected: dev|staging|prod" >&2
      return 1
      ;;
  esac
}

parse_args() {
  env="dev"
  region="us-east-1"
  app_name="meal-expense-tracker"
  secret_name=""

  while [[ $# -gt 0 ]]; do
    case "$1" in
      -e|--env)
        env="$2"
        shift 2
        ;;
      -r|--region)
        region="$2"
        shift 2
        ;;
      -a|--app-name)
        app_name="$2"
        shift 2
        ;;
      --secret-name)
        secret_name="$2"
        shift 2
        ;;
      -h|--help)
        show_usage
        exit 0
        ;;
      *)
        echo "❌ Unknown option: $1" >&2
        show_usage >&2
        exit 1
        ;;
    esac
  done
}

main() {
  local env region app_name secret_name
  parse_args "$@"

  validate_environment "$env"

  if [[ -z "$secret_name" ]]; then
    secret_name="${app_name}/${env}/supabase-connection"
  fi

  echo "🎯 Running database migrations against Supabase..."
  echo ""
  echo "Target environment: $env"
  echo "Secret name: $secret_name"
  echo "AWS region: $region"
  echo ""
  echo "This script will:"
  echo "1. Get the Supabase connection string from AWS Secrets Manager"
  echo "2. Set it as DATABASE_URL"
  echo "3. Run Flask migrations"
  echo ""

  # Get the connection string from AWS Secrets Manager
  local connection_string
  connection_string="$(aws secretsmanager get-secret-value \
    --secret-id "$secret_name" \
    --region "$region" \
    --query SecretString \
    --output text)"

  # Export for Flask
  export DATABASE_URL="$connection_string"

  echo "✅ Retrieved Supabase connection string"
  echo "🔧 Connection: ${connection_string%%:*}" # Just show the protocol part for security
  echo ""

  # Run from project root to ensure Flask app context resolves
  local -r script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  local -r project_root="$(cd "${script_dir}/.." && pwd)"
  cd "$project_root"

  # Activate venv if present
  if [[ -f "$project_root/venv/bin/activate" ]]; then
    # shellcheck disable=SC1091
    source "$project_root/venv/bin/activate"
  fi

  echo "🚀 Running migrations..."
  flask db upgrade

  echo ""
  echo "✅ Migrations complete!"
  echo ""
  echo "Next steps:"
  echo "1. Build and redeploy the Lambda function"
  echo "2. Test the Lambda invocation"
  echo ""
}

main "$@"
