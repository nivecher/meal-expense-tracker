# Development Guide

This document provides detailed instructions for setting up and working with the Meal Expense Tracker project.

## Development Environment Setup

### Prerequisites

- Python 3.13+
- Docker and Docker Compose
- AWS CLI (for deployment)
- AWS SAM CLI (for local Lambda testing)
- Terraform 1.5+ (for infrastructure management)
- **AWS CLI**: For AWS service interaction

### Local Development Setup

### Automated Setup

Run the setup script to configure your development environment:

```bash
## Make the script executable
chmod +x scripts/setup-dev.sh

## Run the setup script
./scripts/setup-dev.sh

```

This script will:

1. Install system dependencies
2. Set up a Python virtual environment
3. Install Python dependencies
4. Configure pre-commit hooks
5. Set up local PostgreSQL container
6. Initialize the database
7. Configure AWS credentials (if not already set up)

### Manual Setup

If you prefer to set up manually:

1. **Clone the repository**

```bash

git clone https://github.com/yourusername/meal-expense-tracker.git
cd meal-expense-tracker

```

1. **Python Environment**

```bash

## Create and activate virtual environment
Python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

## Install dependencies
pip install -r requirements-dev.txt

```

1. **Database Setup**

```bash

## Start PostgreSQL container
docker-compose -f docker-compose.yml up -d postgres

## Run migrations
alembic upgrade head

```

1. **AWS SAM CLI Setup (optional)**

```bash

## Install AWS SAM CLI (Linux)
pip install --user aws-sam-cli

## Verify installation
sam --version

```

1. **LocalStack (Optional, for AWS service emulation)**

```bash

## Install LocalStack
pip install localstack

## Start LocalStack
localstack start -d

```

1. **Configure AWS credentials**

```bash

aws configure
## Follow prompts to enter AWS credentials

```

## Running the Application

### Local Development with Flask

```bash

## Activate virtual environment
source venv/bin/activate

## Set environment variables
export FLASK_APP=wsgi:app
export FLASK_ENV=development

## Start Flask development server
flask run

```

### Local Testing with SAM CLI (optional)

```bash

## Start API Gateway and Lambda locally
sam local start-api --template template.yaml

## Invoke a specific Lambda function
sam local invoke "FunctionName" -e events/event.json

```

### Using Docker Compose

```bash

## Start all services
docker-compose -f docker-compose.yml up -d

## View logs
docker-compose -f docker-compose.yml logs -f

```

## Deployment

### Build and Package (optional)

```bash

## Build deployment package
sam build

## Package for deployment
sam package \
  --output-template-file packaged.yaml \
  --s3-bucket your-deployment-bucket

```

### Deploy to AWS (optional)

```bash

## Deploy to development environment
sam deploy \
  --template-file packaged.yaml \
  --stack-name meal-expense-tracker-dev \
  --capabilities CAPABILITY_IAM \
  --region us-east-1

## Deploy to production
sam deploy \
  --template-file packaged.yaml \
  --stack-name meal-expense-tracker-prod \
  --capabilities CAPABILITY_IAM \
  --region us-east-1

```

### Infrastructure Deployment

```bash

## Initialize Terraform
cd terraform
terraform init

## Plan changes
terraform plan

## Apply changes
terraform apply

```

## Infrastructure Management

### Terraform Commands

```bash

## Initialize Terraform (2)
make tf-init

## Plan infrastructure changes
make tf-plan

## Apply infrastructure changes
make tf-apply

## Destroy infrastructure
make tf-destroy

```

### Running Tests

```bash

## Run all tests
pytest

## Run a specific test file
pytest tests/test_models.py

## Run with coverage report
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
        "FLASK_APP": "wsgi:app",
        "FLASK_ENV": "development"
      },
      "args": ["run", "--no-debugger", "--no-reload"]
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
