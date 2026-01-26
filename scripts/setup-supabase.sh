#!/usr/bin/env bash
# Quick setup script for Supabase migration
# This will save you $95/month!

set -euo pipefail

show_usage() {
  cat <<'EOF'
Usage: ./setup-supabase.sh [options]

Options:
  -e, --env ENV            Target environment (dev|staging|prod). Default: dev
  -r, --region REGION      AWS region for Secrets Manager. Default: us-east-1
  -a, --app-name NAME      App name prefix for secrets. Default: meal-expense-tracker
  -u, --url URL            Supabase connection string (postgres:// or postgresql://). If omitted, you will be prompted.
      --secret-name NAME   Full Secrets Manager secret name override (bypasses app/env defaults)
      --kms-alias ALIAS    KMS alias for *create-secret* (e.g. alias/meal-expense-tracker-staging-main)
      --skip-migrations    Only store secret; do not run flask migrations
  -h, --help               Show this help

Examples:
  ./setup-supabase.sh --env staging
  ./setup-supabase.sh --env staging --url "postgresql://postgres:...@aws-0-us-east-1.pooler.supabase.com:6543/postgres"
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

ensure_pg8000_driver() {
  local url="$1"

  # Add pg8000 driver to connection string if not present
  if [[ "$url" != *"pg8000"* ]]; then
    url="$(echo "$url" | sed 's|postgres://|postgresql+pg8000://|' | sed 's|postgresql://|postgresql+pg8000://|')"
  fi

  echo "$url"
}

parse_args() {
  env="dev"
  region="us-east-1"
  app_name="meal-expense-tracker"
  supabase_url="${SUPABASE_URL:-}"
  secret_name=""
  kms_alias=""
  skip_migrations="false"

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
      -u|--url)
        supabase_url="$2"
        shift 2
        ;;
      --secret-name)
        secret_name="$2"
        shift 2
        ;;
      --kms-alias)
        kms_alias="$2"
        shift 2
        ;;
      --skip-migrations)
        skip_migrations="true"
        shift
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
  local env region app_name supabase_url secret_name kms_alias skip_migrations
  parse_args "$@"

  validate_environment "$env"

  if [[ -z "$secret_name" ]]; then
    secret_name="${app_name}/${env}/supabase-connection"
  fi

  if [[ -z "$kms_alias" ]]; then
    kms_alias="alias/${app_name}-${env}-main"
  fi

  echo "🚀 Setting up Supabase for your meal expense tracker"
  echo ""
  echo "This will save you \$95/month by removing Aurora + RDS Proxy + VPC costs!"
  echo ""
  echo "Target environment: $env"
  echo "Secret name: $secret_name"
  echo "AWS region: $region"
  echo ""

  if [[ -z "$supabase_url" ]]; then
    read -r -p "Enter your Supabase connection string (postgres:// or postgresql://): " supabase_url
  fi

  if [[ -z "$supabase_url" ]]; then
    echo "❌ Connection string is required" >&2
    exit 1
  fi

  echo ""
  echo "📝 Storing Supabase connection in AWS Secrets Manager..."

  supabase_url="$(ensure_pg8000_driver "$supabase_url")"

  # Store in Secrets Manager
  aws secretsmanager create-secret \
    --name "$secret_name" \
    --description "Supabase PostgreSQL connection string for ${app_name} ${env}" \
    --secret-string "$supabase_url" \
    --kms-key-id "$kms_alias" \
    --region "$region" 2>/dev/null || \
  aws secretsmanager update-secret \
    --secret-id "$secret_name" \
    --secret-string "$supabase_url" \
    --region "$region"

  echo "✅ Connection string stored in AWS Secrets Manager"

  if [[ "$skip_migrations" == "true" ]]; then
    echo ""
    echo "✅ Setup complete (migrations skipped)."
    return 0
  fi

  echo ""
  echo "📝 Running database migrations against Supabase..."
  export DATABASE_URL="$supabase_url"

  local -r script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  local -r project_root="$(cd "${script_dir}/.." && pwd)"
  cd "$project_root"

  if [[ -f "$project_root/venv/bin/activate" ]]; then
    # shellcheck disable=SC1091
    source "$project_root/venv/bin/activate"
  fi

  export FLASK_APP="${FLASK_APP:-wsgi:app}"
  flask db upgrade

  echo ""
  echo "✅ Setup complete! Next steps:"
  echo ""
  echo "1. Deploy Terraform for the same environment (Lambda will use DATABASE_SECRET_NAME=${secret_name})"
  echo "2. Redeploy the Lambda image if needed"
  echo ""
  echo "You'll save \$95/month starting now!"
}

main "$@"
