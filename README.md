# 🍽️ Meal Expense Tracker

A modern web application that helps you track dining expenses, analyze spending patterns, and maintain a history of
your culinary experiences.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/python-3.13.5-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.0+-green.svg)](https://flask.palletsprojects.com/)
[![Terraform](https://img.shields.io/badge/terraform-%235835CC.svg?style=flat&logo=terraform&logoColor=white)](https://www.terraform.io/)

## ✨ Features

- **Expense Tracking**
  - Log dining expenses with detailed categorization
  - 9 meal types (breakfast, brunch, lunch, dinner, snacks, drinks, dessert, late night, groceries)
  - Customizable expense categories with colors and icons
  - Advanced filtering and sorting
  - CSV export and bulk import capabilities
  - Tag system for flexible organization

- **Restaurant Management**
  - Save and manage restaurant information
  - Google Maps integration for location services
  - Restaurant search and autocomplete functionality
  - Track visit history and spending statistics
  - Export and import restaurant data

- **User Authentication & Security**
  - Secure user registration and login
  - Password change functionality
  - Admin user management
  - Role-based access control

- **Google Maps Integration**
  - Smart API detection for modern and legacy Google Maps APIs
  - Restaurant search and autocomplete functionality
  - Automatic fallback to ensure compatibility
  - No deprecation warnings

- **Receipt OCR (Optical Character Recognition)**
  - Extract expense data from receipt images/PDFs using AWS Textract
  - Automatic reconciliation of OCR data with form entries
  - Visual comparison of extracted vs entered data
  - One-click application of OCR suggestions
  - **Note:** Requires AWS credentials configured - see Installation section

## 🛠️ Command Line Interface (CLI)

The application provides several useful CLI commands for administration and maintenance:

### Admin User Management

#### Reset Admin Password

Reset the password for an admin user:

```bash
flask reset-admin-password --email admin@example.com

```

You will be prompted to enter and confirm the new password. The password will be securely hashed before being stored in
the database.

**Options:**

- `--email`: Email of the admin user (required)
- `--password`: New password (if not provided, you'll be prompted)

Example:

```bash

flask reset-admin-password --email admin@example.com
## You'll be prompted to enter and confirm the new password

```

## 📦 Version Management

This project uses [setuptools_scm](https://github.com/pypa/setuptools_scm/) for automatic version management based on
Git tags.

### How Versioning Works

- The version is automatically derived from Git tags
- When you create a new Git tag (e.g., `v1.2.3`), `setuptools_scm` will:
  - Generate a version string based on the tag
  - Write it to `app/_version.py` during build/installation
  - The application imports this version at runtime

### Creating a New Release

1. Update the version by creating a new Git tag:

   ```bash

   ## For a new release (e.g., 1.2.3)
   git tag -a v1.2.3 -m "Release v1.2.3"
   git push origin v1.2.3

   ```

1. The next build will automatically use this version

## 🌍 Environment Configuration

The application supports different environment configurations using `.env` files following the `dev`, `test`, and
`prod` naming convention.

### Available Environments

1. **Development** (`.env` or `.env.local`)

- Default environment for local development
  - Debug mode enabled
  - Uses SQLite database by default
  - Run with: `make run`

1. **Testing** (`.env.test` optional)

- Used for running tests
  - Uses a separate test database
  - Debug mode disabled

1. **Production** (`.env.prod` managed by deployment)

- Used in production environments
  - Debug mode disabled
  - Uses PostgreSQL/MySQL database

### Setting Up Environments

1. Copy the example environment file for each environment you need:

   ```bash

   ## For development
   cp .env.example .env

   ## For testing
   cp .env.example .env.test

   ## For production
   cp .env.example .env.prod

   ```

1. Edit each `.env` file with the appropriate configuration values for that environment.

1. Run the application with the desired environment:

   ```bash
   ## For development (default)
   make run
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
   python -c "from app._version import __version__; print(__version__)"
   ```

1. From within the application, the version is available at the `/health` endpoint

## 🚀 Quick Start

### Prerequisites

- **Python 3.13+** (required)
- **AWS Credentials** (required for receipt OCR feature)
  - Configure via environment variables: `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY`
  - Or configure `~/.aws/credentials` file
  - Or use IAM role (for Lambda/ECS deployments)
  - **Note:** The app works without AWS credentials - OCR feature will be disabled if not configured
- **Docker & Docker Compose** (optional, for containerized development)
- **Terraform** (optional, for infrastructure deployment)
- **AWS CLI** (optional, for cloud deployment)

### 🎯 Getting Started (3 Steps)

1. **Clone and setup**:
   ```bash
   git clone https://github.com/yourusername/meal-expense-tracker.git
   cd meal-expense-tracker
   make setup
   ```

2. **Activate environment and run**:
   ```bash
   source venv/bin/activate  # Activate virtual environment
   make run                  # Start the application
   ```

3. **Open your browser**:
   - Visit: http://localhost:5000
   - Default admin: `admin@example.com` / `admin123`

## 🔍 Linting Quick Start

This project uses consistent linting tools across VSCode, Make, pre-commit, and GitHub Actions. All tools are configured to use the same versions and settings.

### Quick Commands

```bash
# Format all code
make format

# Run all linters
make lint

# Format and lint with auto-fix
make lint-fix

# Validate linting tool synchronization
make validate-linting-sync
```

### VSCode Setup

1. **Install recommended extensions**: VSCode will prompt you to install recommended extensions when you open the project
2. **Automatic formatting**: Code is automatically formatted on save
3. **Inline linting**: Linting errors are shown inline with quick fixes available

See [CONTRIBUTING.md](CONTRIBUTING.md#vscode-setup) for detailed VSCode setup instructions.

### Pre-commit Hooks

Pre-commit hooks automatically run on `git commit`:

```bash
# Install hooks (one-time setup)
pre-commit install
pre-commit install --hook-type commit-msg   # Enforce conventional commits

# Run hooks manually
pre-commit run --all-files
```

The **commit-msg** hook uses [commitlint](https://commitlint.js.org/) to validate conventional commit format. Merge commits are allowed. See [docs/BRANCH_NAMING.md](docs/BRANCH_NAMING.md).

### Supported Languages

- **Python**: Ruff, Bandit, MyPy
- **JavaScript**: ESLint
- **HTML**: Prettier
- **CSS**: Stylelint
- **Markdown**: markdownlint, Prettier
- **YAML/JSON/TOML**: Validation and Prettier
- **Terraform**: terraform fmt, terraform validate

For complete linting standards and configuration details, see [docs/LINTING_STANDARDS.md](docs/LINTING_STANDARDS.md).

### 🔧 Development Commands

```bash
# Environment management
make setup          # Complete development setup
make setup-quick    # Quick setup (minimal)
make dev-status     # Check environment status
make reset-dev      # Reset development environment

# Development workflow
make run            # Start development server
make test           # Run all tests
make check          # Run all quality checks (format + lint + test)
make security-scan  # Check for security vulnerabilities

# Database management
make db-upgrade     # Run database migrations
make db-reset       # Reset database (development only)
```

### 🧪 Testing & Quality

```bash
# Testing
make test              # Run all tests with coverage
make test-unit         # Run only unit tests
make test-integration  # Run only integration tests
make test-frontend     # Run frontend tests (Playwright)

# Code quality
make format            # Format code (Python, HTML, CSS, JS)
make lint              # Run all linters
make lint-fix          # Run linters with auto-fix
make check             # Run all quality checks
make security-scan     # Security vulnerability scan
```

### 📦 Requirements & Dependencies

**Python Dependencies:**
All Python dependencies are pinned in `requirements.txt` and `requirements-dev.txt`. Install with:
```bash
pip install -r requirements.txt  # Production dependencies
pip install -r requirements-dev.txt  # Development dependencies
```

**Optional Script Dependencies:**
Some utility scripts (like `scripts/extract_receipt.py`) require additional dependencies that are NOT needed for production:
```bash
# Install script dependencies (includes EasyOCR for local OCR processing)
pip install -r requirements/scripts.txt
```
Note: The production application uses AWS Textract for OCR, not EasyOCR. EasyOCR is only needed for the standalone receipt extraction script.

**AWS Configuration:**
- **AWS Textract** (required for receipt OCR feature)
  - Required only if you want OCR functionality
  - Configure AWS credentials via environment variables, `~/.aws/credentials`, or IAM role
  - See Prerequisites section above for configuration instructions
  - The application gracefully handles missing AWS credentials - OCR simply won't be available

```bash
# Requirements management
make requirements      # Generate requirements from .in files
make deps-check        # Check for outdated dependencies
make deps-update       # Update dependencies to latest versions
make install-deps      # Install production dependencies
make install-dev-deps  # Install development dependencies
```

#### JavaScript

The project uses ESLint for JavaScript linting with the following configuration:

- **ESLint Version**: 9.32.0+
- **Configuration File**: `eslint.config.js`
- **Rules**: Custom rules for different environments and file types

##### Running JavaScript Linter

```bash
## Lint all JavaScript files
make lint-js

## Lint and fix auto-fixable issues
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

## Basic initialization (development environment)
python init_db.py

## Initialize for a specific environment
python init_db.py --env=testing

## Reset database (drops all tables and recreates them)
python init_db.py --reset

## Run database migrations after initialization
python init_db.py --migrate

## Combine options (reset and migrate)
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

The script respects the application's environment configuration, ensuring proper database connection settings for each
environment.

## 🧪 Browser Automation & Testing

The project includes comprehensive browser automation and testing capabilities using the Model Context Protocol (MCP):

### MCP Browser Automation

- **Console Debugging**: Automated browser console error detection and analysis
- **End-to-End Testing**: Comprehensive browser automation for testing user flows
- **Performance Monitoring**: Real-time performance analysis during browser interactions
- **Cross-Browser Testing**: Support for multiple browser engines via Playwright

### 🚀 Advanced Setup Options

#### MCP (Model Context Protocol) Integration

1. **Install MCP Server**:
   ```bash
   ./scripts/setup-mcp.sh
   ```

2. **Run Health Check**:
   ```bash
   # In Cursor with MCP enabled
   node scripts/mcp-health-check.js
   ```

3. **Debug Console Issues**:
   ```bash
   # In Cursor with MCP enabled
   node scripts/mcp-console-debug.js
   ```

#### Containerized Development

```bash
# Start all services with Docker Compose
make docker-up

# View logs
make docker-logs

# Stop services
make docker-down
```

#### Infrastructure Deployment

```bash
# Initialize Terraform
make tf-init

# Plan infrastructure changes
make tf-plan

# Deploy to development (Lambda + frontend assets)
make deploy

# Redeploy Lambda only
make redeploy-dev

# Sync frontend assets only
make deploy-static
```

1. **Run Browser Tests**:
   ```bash
   # In Cursor with MCP enabled
   node scripts/test-mcp.js
   ```

### MCP Documentation

- [MCP Browser Quick Reference](docs/MCP_BROWSER_QUICK_REFERENCE.md) - Quick commands and setup
- [MCP Console Debugging Guide](docs/BROWSER_MCP_CONSOLE_DEBUGGING.md) - Detailed debugging workflow
- [MCP Troubleshooting Guide](docs/MCP_TROUBLESHOOTING.md) - Common issues and solutions

## 📚 Documentation

- [Architecture](docs/ARCHITECTURE.md) - High-level system design
- [Development Guide](docs/DEVELOPMENT.md) - Setup and workflow
- [Technology Stack](docs/TECHNOLOGY.md) - Detailed technology choices
- [ADRs](docs/architecture/decisions/) - Architecture Decision Records

## 🛠️ Development

### Code Quality

```bash
## Run all quality checks
make quality

## Run linters
make lint

## Format code
make format

## Run tests
make test

## Run tests with coverage
make test-cov
```

### Code Quality with Pre-commit

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

   > **Note**: For Google Maps API integration details, see [Google Maps API Guide](docs/GOOGLE_MAPS_API.md)

   ```

1. **Install dependencies** using pip-tools:

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
- `requirements/scripts.in` - Optional dependencies for utility scripts (EasyOCR, pdf2image)

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
## Run tests
make test

## Run linters
make lint

## Format code
make format

## Check for security issues
make security-check
```

## 📦 Packaging (Container Image)

### Packaging Prerequisites

- Docker
- AWS CLI (optional, for ECR push)

### Build and Push the Container Image

```bash
# Build container image
./scripts/package-docker-lambda.sh --arm64

# Push to ECR
./scripts/package-docker-lambda.sh --push --arm64
```

## 🚀 AWS Lambda Deployment (Containerized)

### Deployment Prerequisites

- AWS Account with appropriate permissions
- AWS CLI configured with credentials
- ECR repository and Lambda function configured for container images

### Deploying the Lambda Function

For ad-hoc dev deployments, use:

```bash
./scripts/redeploy-lambda.sh
```

For staging/prod, use the GitHub Actions deploy workflow (container image-based).

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
  --function-name "$LAMBDA_FUNCTION_NAME" \
  --payload '{"httpMethod": "GET", "path": "/health"}' \
  response.json

# View the response
cat response.json
```

### CI/CD Integration

For automated deployments, you can integrate this into your CI/CD pipeline. The repository includes a GitHub Actions
workflow that can be configured to build and deploy the container image on push to specific branches.

### Troubleshooting

- **Image Size Issues**: Ensure your container image is optimized. The Lambda service has a maximum container image size limit.
- **Permissions**: Make sure your IAM roles have the necessary permissions for ECR and Lambda.
- **Cold Starts**: Consider configuring provisioned concurrency if you experience cold start latency issues.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
