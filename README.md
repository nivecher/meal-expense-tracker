# 🍽️ Meal Expense Tracker

A modern web application that helps you track dining expenses, analyze spending patterns, and maintain a history of your culinary experiences.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/)
[![Terraform](https://img.shields.io/badge/terraform-%235835CC.svg?style=flat&logo=terraform&logoColor=white)](https://www.terraform.io/)

## ✨ Features

- **Expense Tracking**
  - Log dining expenses with photos and receipts
  - Categorize by meal type and restaurant
  - Track spending patterns over time

- **Restaurant Management**
  - Save favorite dining spots
  - Rate and review restaurants
  - Track visit history

- **Insights & Reporting**
  - Visual spending analytics
  - Budget tracking
  - Exportable reports

## 🛠️ Command Line Interface (CLI)

The application provides several useful CLI commands for administration and maintenance:

### Admin User Management

#### Reset Admin Password

Reset the password for an admin user:

```bash
flask reset-admin-password --email admin@example.com
```

You will be prompted to enter and confirm the new password. The password will be securely hashed before being stored in the database.

**Options:**
- `--email`: Email of the admin user (required)
- `--password`: New password (if not provided, you'll be prompted)

Example:
```bash
flask reset-admin-password --email admin@example.com
# You'll be prompted to enter and confirm the new password
```

## 📦 Version Management

This project uses [setuptools_scm](https://github.com/pypa/setuptools_scm/) for automatic version management based on Git tags.

### How Versioning Works

- The version is automatically derived from Git tags
- When you create a new Git tag (e.g., `v1.2.3`), `setuptools_scm` will:
  - Generate a version string based on the tag
  - Write it to `app/_version.py` during build/installation
  - The application imports this version at runtime

### Creating a New Release

1. Update the version by creating a new Git tag:

   ```bash
   # For a new release (e.g., 1.2.3)
   git tag -a v1.2.3 -m "Release v1.2.3"
   git push origin v1.2.3
   ```

2. The next build will automatically use this version

## 🌍 Environment Configuration

The application supports different environment configurations using `.env` files following the `dev`, `test`, and `prod` naming convention.

### Available Environments

1. **Development** (`.env.dev`)
   - Default environment for local development
   - Debug mode enabled
   - Uses SQLite database by default
   - Run with: `python scripts/run.py dev` or just `python scripts/run.py`

2. **Testing** (`.env.test`)
   - Used for running tests
   - Uses a separate test database
   - Debug mode disabled
   - Run with: `python scripts/run.py test`

3. **Production** (`.env.prod`)
   - Used in production environments
   - Debug mode disabled
   - Uses PostgreSQL/MySQL database
   - Run with: `python scripts/run.py prod`

### Setting Up Environments

1. Copy the example environment file for each environment you need:

   ```bash
   # For development
   cp env.example .env.dev

   # For testing
   cp env.example .env.test

   # For production
   cp env.example .env.prod
   ```

2. Edit each `.env` file with the appropriate configuration values for that environment.

3. Run the application with the desired environment:

   ```bash
   # For development (default)
   python scripts/run.py dev

   # For testing
   python scripts/run.py test

   # For production
   python scripts/run.py prod
   ```

### Environment Variables

Key environment variables (set in each `.env` file):

- `FLASK_APP`: Entry point of the application (default: `wsgi:app`)
- `FLASK_ENV`: Environment (`development` for dev, `production` otherwise)
- `SECRET_KEY`: Secret key for session security
- `DATABASE_URL`: Database connection URL
- `DEBUG`: Set to `True` for development
- `DATABASE_URL`: Database connection URL
- `AWS_*`: AWS credentials (if using AWS services)
- `MAIL_*`: Email configuration

### Development Version

- When running from source without installation, the version will be `0.0.0.dev0`
- This helps distinguish between development and released versions

### Checking the Current Version

You can check the current version in several ways:

1. From the command line:

   ```bash
   python -c "from app import version; print(version['app'])"
   ```

2. From within the application, the version is available at the `/health` endpoint

## 🚀 Quick Start

### Initial Prerequisites

- Python 3.13+
- Docker & Docker Compose
- Terraform (for infrastructure)
- AWS CLI (for deployment)

### Local Development Setup

1. Clone the repository:

   ```bash
   git clone https://github.com/yourusername/meal-expense-tracker.git
   cd meal-expense-tracker
   ```

2. **Run the setup script**

   ```bash
   chmod +x scripts/setup-local-dev.sh
   ./scripts/setup-local-dev.sh
   ```

3. Initialize the database:

   ```bash
   flask db upgrade
   ```

4. Run the development server:

   ```bash
   flask run
   ```

### Running Tests

```bash
# Run all tests
pytest

# Run tests with coverage report
pytest --cov=app --cov-report=term-missing
```

### Linting and Formatting

#### Python

```bash
# Run flake8
flake8 app tests

# Run black
black app tests

# Run isort
isort app tests
```

#### JavaScript

The project uses ESLint for JavaScript linting with the following configuration:

- **ESLint Version**: 9.32.0+
- **Configuration File**: `eslint.config.js`
- **Rules**: Custom rules for different environments and file types

##### Running JavaScript Linter

```bash
# Lint all JavaScript files
yarn lint:js
# or
make lint-js

# Lint and fix auto-fixable issues
yarn lint:js:fix
# or
make lint-js-fix
```

##### Linting Modes

- **Development Mode** (`NODE_ENV=development`):
  - Console statements are allowed
  - Unused variables are warned about
  - More lenient rules for development

- **Production Mode** (default):
  - Console statements are treated as errors
  - Stricter rules for production code

##### Configuration Highlights

- Uses modern ESLint flat config format
- Environment-specific rules for different file types
- Custom rules for test files, components, and utilities
- Integration with Makefile for consistent development workflow

##### Ignored Files

- `node_modules/`
- `dist/`
- `build/`
- `coverage/`
- Test files (`*.test.js`, `*-test.js`) have special rules

## 🗄️ Database Management

The application includes a utility script for database initialization and management:

### Initializing the Database

```bash
# Basic initialization (development environment)
python init_db.py

# Initialize for a specific environment
python init_db.py --env=testing

# Reset database (drops all tables and recreates them)
python init_db.py --reset

# Run database migrations after initialization
python init_db.py --migrate

# Combine options (reset and migrate)
python init_db.py --reset --migrate
```

### Available Options

- `--env`: Environment to use (default: development)
  - Choices: development, testing, production
- `--reset`: Drop all tables before creating them
- `--migrate`: Run database migrations after initialization

### Safety Features

- The script will prompt for confirmation before dropping tables
- Uses proper transaction management for database operations
- Includes comprehensive error handling and logging

### Environment Configuration

The script respects the application's environment configuration, ensuring proper database connection settings for each environment.

## 📚 Documentation

- [Architecture](docs/ARCHITECTURE.md) - High-level system design
- [Development Guide](docs/DEVELOPMENT.md) - Setup and workflow
- [Technology Stack](docs/TECHNOLOGY.md) - Detailed technology choices
- [ADRs](docs/architecture/decisions/) - Architecture Decision Records

## 🛠️ Development

### Code Quality

```bash
# Run linters
make lint

# Format code
make format

# Run tests
make test

# Run tests with coverage
make test-cov
```

### Pre-commit Hooks

This project uses pre-commit to maintain code quality. Hooks are automatically installed during setup.

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details on how to get started.

### Environment Setup

1. **Create a `.env` file** with these variables:

   ```env
   FLASK_APP=wsgi:app
   FLASK_ENV=development
   SECRET_KEY=your-secret-key
   SQLALCHEMY_DATABASE_URI=sqlite:///instance/meals_expenses.db
   GOOGLE_MAPS_API_KEY=your-google-api-key
   GOOGLE_MAPS_MAP_ID=your-google-map-id
   ```

2. **Install dependencies** using pip-tools:

   ```bash
   pip install pip-tools
   pip-sync requirements.txt requirements-dev.txt
   ```

### 📦 Requirements Management

This project uses a structured approach to manage Python dependencies:

- `requirements/base.in` - Core dependencies required in all environments
- `requirements/dev.in` - Development-specific dependencies
- `requirements/test.in` - Testing dependencies
- `requirements/prod.in` - Production-specific dependencies

To update the requirements:

1. Edit the appropriate `.in` file in the `requirements/` directory
2. Run the following command to compile the requirements:

   ```bash
   make requirements
   ```

3. Install the updated requirements:

   ```bash
   pip-sync requirements.txt requirements-dev.txt
   ```

4. **Run the development server**:

   ```bash
   make run
   ```

### Common Development Tasks

```bash
# Run tests
make test

# Run linters
make lint

# Format code
make format

# Check for security issues
make security-check
```

## 📦 Packaging

### Packaging Prerequisites

- Python 3.13+
- pip
- AWS CLI (if deploying to AWS)

### Package the Application

We provide a unified script to package both the application and its dependencies:

```bash
# Package both application and dependencies layer (default)
./scripts/package.sh

# Or package just the application
./scripts/package.sh --app

# Or just the dependencies layer
./scripts/package.sh --layer
```

This will create the following files:

- `dist/app.zip` - The application package
- `dist/layers/python-dependencies.zip` - The dependencies layer

## 🚀 AWS Lambda Deployment

### Deployment Prerequisites

- AWS Account with appropriate permissions
- AWS CLI configured with credentials
- AWS S3 bucket for deployment packages
- AWS Lambda function configured

### Deploying the Lambda Function

1. **Package the Application**

   ```bash
   # Create the deployment package
   make package-lambda
   ```

   This will create:
   - `dist/app.zip` - The application package
   - `dist/layers/python-dependencies.zip` - The dependencies layer

2. **Deploy to Lambda**

   ```bash
   # Deploy the ZIP package to Lambda
   aws lambda update-function-code \
     --function-name your-lambda-function-name \
     --zip-file fileb://dist/app.zip
   ```

### Lambda Environment Variables

Make sure to set the following environment variables in your Lambda function:

- `FLASK_APP=wsgi:app`
- `FLASK_ENV=production`
- `SQLALCHEMY_DATABASE_URI` - Your database connection string
- `SECRET_KEY` - A secure secret key for Flask
- Any other required configuration variables

### Testing the Deployment

After deployment, you can test your Lambda function:

```bash
# Invoke the function directly
aws lambda invoke \
  --function-name $LAMBDA_FUNCTION_NAME \
  --payload '{"httpMethod": "GET", "path": "/health"}' \
  response.json

# View the response
cat response.json
```

### CI/CD Integration

For automated deployments, you can integrate this into your CI/CD pipeline. The repository includes a GitHub Actions workflow that can be configured to build and deploy the container image on push to specific branches.

### Troubleshooting

- **Image Size Issues**: Ensure your container image is optimized. The Lambda service has a maximum container image size limit.
- **Permissions**: Make sure your IAM roles have the necessary permissions for ECR and Lambda.
- **Cold Starts**: Consider configuring provisioned concurrency if you experience cold start latency issues.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
