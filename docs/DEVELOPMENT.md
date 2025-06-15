# Development Guide

This document provides detailed instructions for setting up and working with the Meal Expense Tracker project.

## 🛠 Development Environment Setup

### Prerequisites

- **Python 3.9+**: For running the application and development tools
- **pip**: Python package manager
- **Git**: Version control system
- **Docker & Docker Compose**: For containerized development
- **Go (optional)**: For installing `shfmt` shell formatter

### Automated Setup (Recommended)

Run the setup script to configure your development environment:

```bash
# Make the script executable
chmod +x scripts/setup-local-dev.sh

# Run the setup script
./scripts/setup-local-dev.sh
```

This script will:
1. Install system dependencies
2. Set up a Python virtual environment
3. Install Python dependencies
4. Configure pre-commit hooks
5. Set up Docker containers
6. Initialize the database

### Manual Setup

If you prefer to set up manually:

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/meal-expense-tracker.git
   cd meal-expense-tracker
   ```

2. **Set up Python environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install --upgrade pip
   pip install -r requirements-dev.txt
   ```

3. **Install development tools**
   ```bash
   # Install pre-commit hooks
   pre-commit install

   # Install shellcheck (Linux)
   sudo apt-get install shellcheck

   # Install shfmt (recommended)
   go install mvdan.cc/sh/v3/cmd/shfmt@latest
   ```

## 🚀 Running the Application

### Development Server

```bash
# Activate virtual environment
source venv/bin/activate

# Start Flask development server
flask run
```

Access the application at: http://localhost:5000

### Using Docker

```bash
# Build and start containers
docker-compose up -d --build

# View logs
docker-compose logs -f
```

## 🔧 Development Tools

### Pre-commit Hooks

This project uses pre-commit to run checks before each commit. The following hooks are configured:

- **Black**: Python code formatting
- **Flake8**: Python linting
- **ShellCheck**: Shell script linting
- **shfmt**: Shell script formatting
- **Terraform fmt**: Terraform code formatting

To run all hooks manually:
```bash
pre-commit run --all-files
```

### Makefile Commands

Common development tasks are automated using the Makefile:

```bash
# Format code
make format

# Run tests
make test

# Run tests with coverage
make test-cov

# Lint code
make lint

# Run security checks
make security
```

## 🧪 Testing

### Running Tests

```bash
# Run all tests
pytest

# Run a specific test file
pytest tests/test_models.py

# Run with coverage report
pytest --cov=app --cov-report=term-missing
```

### Test Coverage

To generate an HTML coverage report:
```bash
pytest --cov=app --cov-report=html
open htmlcov/index.html  # View the report
```

## 🐛 Debugging

### VS Code Configuration

Add this to your `.vscode/launch.json` for debugging:

```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Python: Flask",
            "type": "python",
            "request": "launch",
            "module": "flask",
            "env": {
                "FLASK_APP": "app.py",
                "FLASK_ENV": "development"
            },
            "args": [
                "run",
                "--no-debugger",
                "--no-reload"
            ]
        }
    ]
}
```

## 🤝 Contributing

1. Create a new branch for your feature
2. Make your changes
3. Run tests and linters
4. Commit your changes with a descriptive message
5. Push to your fork and open a pull request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
