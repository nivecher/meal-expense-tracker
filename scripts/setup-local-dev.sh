#!/bin/bash

# Exit on error
set -e

echo "Setting up local development environment..."

echo "Installing Python dependencies..."
pip install --upgrade pip
pip install pip-tools

# Create requirements files if they don't exist
if [ ! -f requirements.in ]; then
    echo "Creating requirements.in..."
    echo "Flask>=3.1.1" > requirements.in
    echo "Flask-SQLAlchemy>=3.1.1" >> requirements.in
    echo "Flask-Login>=0.6.3" >> requirements.in
    echo "Flask-Migrate>=4.0.5" >> requirements.in
    echo "Flask-WTF>=1.2.1" >> requirements.in
    echo "psycopg2-binary>=2.9.9" >> requirements.in
    echo "python-dotenv>=1.0.0" >> requirements.in
    echo "boto3>=1.38.32" >> requirements.in
    echo "botocore>=1.38.32" >> requirements.in
fi

if [ ! -f requirements-dev.in ]; then
    echo "Creating requirements-dev.in..."
    echo "-r requirements.in" > requirements-dev.in
    echo "pytest>=7.4.3" >> requirements-dev.in
    echo "pytest-cov>=4.1.0" >> requirements-dev.in
    echo "black>=23.11.0" >> requirements-dev.in
    echo "flake8>=6.1.0" >> requirements-dev.in
    echo "mypy>=1.6.1" >> requirements-dev.in
    echo "mypy-extensions>=1.1.0" >> requirements-dev.in
    echo "bandit>=1.7.5" >> requirements-dev.in
    echo "checkov>=3.2.437" >> requirements-dev.in
    echo "typing-extensions>=4.4.0" >> requirements-dev.in
    echo "sphinx>=7.1.2" >> requirements-dev.in
    echo "sphinx-rtd-theme>=1.3.0" >> requirements-dev.in
    echo "pre-commit>=3.3.3" >> requirements-dev.in
    echo "ipython>=8.12.0" >> requirements-dev.in
fi

# Generate requirements files
pip-compile requirements.in
pip-compile requirements-dev.in

# Install dependencies
pip install -r requirements-dev.txt
echo "Skipping package installation due to setuptools-scm versioning issues"

# Install pre-commit hooks
echo "Installing pre-commit hooks..."
pip install pre-commit
pre-commit install --install-hooks

# Install security scanning tools
echo "Installing security scanning tools..."
pip install bandit checkov

# Install Docker and Docker Compose
echo "Installing Docker..."
sudo apt-get update
sudo apt-get install -y docker.io docker-compose
sudo usermod -aG docker $USER

# Update version from git tags
python scripts/update-version.py

# Exit if version update failed
if [ $? -ne 0 ]; then
    echo "Error: Failed to update version from git tags"
    exit 1
fi

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "Creating .env file..."
    echo "FLASK_APP=app.py" > .env
    echo "FLASK_ENV=development" >> .env
    echo "DATABASE_URL=postgresql://localhost:5432/meal_expenses" >> .env
    echo "SECRET_KEY=your-secret-key-here" >> .env
fi

# Initialize database
echo "Initializing database..."
python init_db.py

# Build and start containers
echo "Building and starting containers..."
docker-compose up -d --build

# Run security scans
echo "Running security scans..."
bandit -r app/

# Run code quality checks
echo "Running code quality checks..."
black . --check
flake8 app/
mypy app/

echo "Local development environment setup complete!"
echo "Access the application at http://localhost:5000"
