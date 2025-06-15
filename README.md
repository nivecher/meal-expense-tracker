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

## 🚀 Quick Start

### Prerequisites

- Python 3.9+
- Docker & Docker Compose
- Terraform (for infrastructure)
- AWS CLI (for deployment)

### Local Development

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/meal-expense-tracker.git
   cd meal-expense-tracker
   ```

2. **Run the setup script**
   ```bash
   chmod +x scripts/setup-local-dev.sh
   ./scripts/setup-local-dev.sh
   ```

3. **Start the development server**
   ```bash
   # Activate virtual environment
   source venv/bin/activate

   # Start the application
   flask run
   ```

4. **Access the application**
   Open your browser and navigate to: http://localhost:5000

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
   FLASK_APP=wsgi.py
   FLASK_ENV=development
   SECRET_KEY=your-secret-key
   SQLALCHEMY_DATABASE_URI=sqlite:///instance/meals.db
   GOOGLE_MAPS_API_KEY=your-google-api-key
   ```

2. **Install dependencies** using pip-tools:
   ```bash
   pip install pip-tools
   pip-sync requirements/requirements.txt requirements/requirements-dev.txt
   ```

### 📦 Requirements Management

This project uses a structured approach to manage Python dependencies:

- `requirements/base.in` - Core application dependencies
- `requirements/dev.in` - Development tools and testing dependencies
- `requirements/prod.in` - Production-specific dependencies
- `requirements/security.in` - Security scanning tools

To update dependencies:

1. Edit the appropriate `.in` file
2. Compile the requirements:
   ```bash
   pip-compile requirements/base.in -o requirements/requirements.txt
   pip-compile requirements/dev.in -o requirements/requirements-dev.txt
   ```
3. Install the updated requirements:
   ```bash
   pip-sync requirements/requirements.txt requirements/requirements-dev.txt
   ```

3. **Run the development server**:
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

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
