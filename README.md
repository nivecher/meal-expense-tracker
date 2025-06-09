# 🍽️ Meal Expense Tracker

A modern web application that helps you track dining expenses, analyze spending patterns, and maintain a history of your culinary experiences.

## ✨ Key Features

- **Effortless Tracking**
  - Quick expense logging with auto-complete
  - Google Places API integration for accurate location data
  - Categorize expenses by meal type (Breakfast, Lunch, Dinner, etc.)

- **Smart Insights**
  - Visual spending reports and analytics
  - Track dining trends over time
  - Set and manage dining budgets

- **Restaurant Management**
  - Save favorite dining spots
  - View visit history and spending per location
  - Add notes and ratings for future reference

- **Health & Habits**
  - Monitor dining frequency and patterns
  - Make informed choices about eating out
  - Track progress toward personal goals

## 🚀 Quick Start

### Prerequisites

#### System Dependencies
- Python 3.11 (Recommended: 3.11.0)
- pip (Python package installer)
- SQLite development package:
  ```bash
  # On Debian/Ubuntu
  sudo apt-get update && sudo apt-get install -y libsqlite3-dev
  
  # On RHEL/CentOS
  sudo yum install -y sqlite-devel
  
  # On macOS (with Homebrew)
  brew install sqlite
  ```

#### Optional Dependencies
- Docker (for containerized deployment)
- Google Places API key (for location services)
- tfsec (for Terraform security scanning)

#### Development Setup
We provide a setup script to configure your development environment:
```bash
# Make the script executable
chmod +x scripts/setup-local-dev.sh

# Run the setup script
./scripts/setup-local-dev.sh
```

This script will:
1. Install system dependencies
2. Set up a Python virtual environment
3. Install all required Python packages
4. Configure pre-commit hooks

### Python Virtual Environment

We recommend using a virtual environment to manage dependencies. Here's how to set it up:

1. **Create a virtual environment**:
   ```bash
   # On Unix/macOS
   python3 -m venv venv
   
   # On Windows
   python -m venv venv
   ```

2. **Activate the virtual environment**:
   ```bash
   # On Unix/macOS
   source venv/bin/activate
   
   # On Windows (Command Prompt)
   venv\Scripts\activate.bat
   
   # On Windows (PowerShell)
   .\venv\Scripts\Activate.ps1
   ```

3. **Upgrade pip and setuptools**:
   ```bash
   pip install --upgrade pip setuptools
   ```

4. **Deactivate when done**:
   ```bash
   deactivate
   ```

   > 💡 **Tip**: Add `venv/` to your `.gitignore` (already included in this project) to avoid committing the virtual environment.

### TFSec Security Scanning

This project uses [TFSec](https://aquasecurity.github.io/tfsec/) to scan Terraform configurations for potential security issues. TFSec is integrated into the pre-commit hooks and will run automatically on commits that include `.tf` files.

#### Installation

```bash
# macOS
brew install tfsec

# Linux
curl -s https://raw.githubusercontent.com/aquasecurity/tfsec/master/scripts/install_linux.sh | bash

# Windows (using Chocolatey)
choco install tfsec
```

#### Usage

Run TFSec manually:
```bash
tfsec .
```

#### Configuration

- Customize TFSec behavior by editing `.tfsec.yml`
- Ignore specific checks using `# tfsec:ignore:CHECK_ID` comments in your Terraform files
- View detailed documentation in [docs/tfsec.md](docs/tfsec.md)

### Local Development

1. **Clone and setup**
   ```bash
   git clone <repo-url>
   cd meal-expense-tracker
   
   # Create and activate virtual environment (if not already done)
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   
   # Install development dependencies
   make setup
   ```

2. **Configure environment**
   ```bash
   cp .env.sample .env
   # Edit .env with your configuration
   ```
v
3. **Run the application**
   ```bash
   make run  # For local development
   # or
   make docker-rebuild  # For Docker-based development
   ```

4. **Access the app**
   - Local: http://localhost:5000
   - Docker: http://localhost:5000

### Environment Variables

Create a `.env` file with these variables:

```env
FLASK_APP=wsgi.py
FLASK_ENV=development
SECRET_KEY=your-secret-key
SQLALCHEMY_DATABASE_URI=sqlite:///instance/meals.db
GOOGLE_MAPS_API_KEY=your-google-api-key
```

## 🛠 Development

### Dependency Management

We use `pip-tools` to manage Python dependencies. The requirements are split into multiple files:

- `requirements/base.in` - Core application dependencies
- `requirements/dev.in` - Development tools and testing dependencies
- `requirements/prod.in` - Production-specific dependencies
- `requirements/security.in` - Security scanning tools

#### Setting Up Dependencies

1. Install pip-tools:
   ```bash
   pip install pip-tools
   ```

2. Install development dependencies:
   ```bash
   pip-sync requirements/requirements.txt requirements/dev-requirements.txt
   ```

3. Update requirements files:
   ```bash
   ./scripts/update_requirements.sh
   ```

### Common Tasks

```bash
# Run tests
make test

# Run linters
make lint

# Format code
make format

# Check for security vulnerabilities
make security-check

# Update dependencies
make update-deps
```

### Database Management

```bash
# Initialize database
make db-init

# Create new migration
make db-migrate

# Apply migrations
make db-upgrade
```

## 🚀 Deployment

### Local Deployment

```bash
make deploy-dev  # Development
make deploy-staging  # Staging
make deploy-prod   # Production
```

### Docker Deployment

```bash
# Build and run
make docker-build
make docker-run

# View logs
make docker-logs

# Stop containers
make docker-stop
```

## License

MIT License
