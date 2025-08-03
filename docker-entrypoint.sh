#!/bin/bash
set -e

# Function to wait for database to be ready
wait_for_db() {
  local max_retries=30
  local retry_count=0
  local db_host="$1"
  local db_port="$2"
  local db_user="$3"
  local db_password="$4"
  local db_name="$5"

  echo "Waiting for database to be ready at ${db_host}:${db_port}..."
  until PGPASSWORD="${db_password}" psql -h "${db_host}" -p "${db_port}" -U "${db_user}" -d "${db_name}" -c '\q' 2>/dev/null; do
    retry_count=$((retry_count + 1))
    if [ $retry_count -ge $max_retries ]; then
      echo "Failed to connect to database after ${max_retries} attempts"
      return 1
    fi
    echo "Database is unavailable - sleeping (attempt ${retry_count}/${max_retries})"
    sleep 2
  done
  echo "Database is up and running!"
}

# Function to initialize the database
init_database() {
  echo "Initializing database..."

  # Create database if it doesn't exist (PostgreSQL specific)
  if [ "${DB_ENGINE}" = "postgresql" ]; then
    PGPASSWORD="${DB_PASSWORD}" createdb -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USERNAME}" "${DB_NAME}" 2>/dev/null || true
  fi

  # Run database migrations
  echo "Running database migrations..."
  flask db upgrade

  # Create default admin user if it doesn't exist
  echo "Ensuring default admin user exists..."
  python -c "
import os
from app import create_app
from app.auth.models import User
from app.extensions import db

app = create_app()
with app.app_context():
    if not User.query.filter_by(username='admin').first():
        admin = User(
            username=os.environ.get('DEFAULT_ADMIN_USERNAME', 'admin'),
            email=os.environ.get('DEFAULT_ADMIN_EMAIL', 'admin@example.com'),
            is_admin=True,
            is_active=True
        )
        admin.set_password(os.environ.get('DEFAULT_ADMIN_PASSWORD', 'admin'))
        db.session.add(admin)
        db.session.commit()
        print('Created default admin user')
    else:
        print('Admin user already exists')
"
}

# Main execution
if [ "${DB_ENGINE}" = "postgresql" ]; then
  wait_for_db \
    "${DB_HOST}" \
    "${DB_PORT:-5432}" \
    "${DB_USERNAME}" \
    "${DB_PASSWORD}" \
    "${DB_NAME}" || exit 1
fi

# Initialize database if needed
if [ "${SKIP_DB_INIT:-false}" != "true" ]; then
  init_database
else
  echo "Skipping database initialization (SKIP_DB_INIT=${SKIP_DB_INIT})"
fi

# Execute the command passed to the container
exec "$@"
