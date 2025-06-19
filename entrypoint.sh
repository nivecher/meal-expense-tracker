#!/bin/bash
set -e

# Function to wait for database to be ready
wait_for_db() {
  echo "Waiting for database to be ready..."
  until PGPASSWORD=$DB_PASSWORD psql -h "$DB_HOST" -U "$DB_USERNAME" -d "$DB_NAME" -c '\q' 2>/dev/null; do
    echo "Database is unavailable - sleeping"
    sleep 1
  done
  echo "Database is up and running!"
}

# Only wait for DB if we're not running in Lambda
if [ -z "${AWS_LAMBDA_FUNCTION_NAME}" ]; then
  wait_for_db
fi

# Run database migrations if needed
if [ "$RUN_MIGRATIONS" = "true" ]; then
  echo "Running database migrations..."
  flask db upgrade
fi

# Execute the command passed to the container
exec "$@"
