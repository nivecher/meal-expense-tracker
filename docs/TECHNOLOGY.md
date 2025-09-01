# Technology Stack

This document outlines the technology choices and architecture decisions for the Meal Expense Tracker application.

## Table of Contents

- [Core Technologies](#core-technologies)
- [Infrastructure](#infrastructure)
- [Development Tools](#development-tools)
- [CI/CD Pipeline](#cicd-pipeline)
- [Security](#security)
- [Monitoring and Operations](#monitoring-and-operations)
- [Future Considerations](#future-considerations)

## Core Technologies

### Backend

- **Language**: [Python 3.13](https://www.python.org/)
  - Type hints and modern Python features
  - Strict typing with Mypy for better code quality

- **Web Framework**: [Flask 3.1.1](https://flask.palletsprojects.com/)
  - Blueprints for modular application structure
  - AWS Lambda WSGI adapter for serverless deployment

- **Database**: [SQLAlchemy 2.0](https://www.sqlalchemy.org/)
  - Modern SQLAlchemy with improved type hints
  - PostgreSQL for production, SQLite for development
  - Flask-Migrate for schema management

- **Data & Validation**: 
  - [Marshmallow](https://marshmallow.readthedocs.io/) for API serialization/validation
  - [msgspec](https://jcristharif.com/msgspec/) for high-performance JSON serialization
  - [WTForms](https://wtforms.readthedocs.io/) for form validation

- **Authentication & Security**:
  - Flask-Login for session-based authentication
  - JWT for API token authentication
  - Flexible session storage (DynamoDB for AWS, signed cookies for Lambda)
  - Flask-Limiter for rate limiting
  - CSRF protection (disabled in Lambda, enabled in development)

- **Testing**: Pytest with comprehensive test fixtures
- **Code Quality**: Black, isort, Flake8, Mypy, pre-commit hooks

### Frontend

- **Framework Strategy**: Server-side rendered templates with progressive enhancement
  - [Jinja2](https://jinja.palletsprojects.com/) templates for server-side rendering
  - [Bootstrap 5.3.3](https://getbootstrap.com/) for responsive UI components
  - [jQuery 3.7.1](https://jquery.com/) for DOM manipulation and AJAX
  - Vanilla JavaScript ES6+ for modern features and custom components

- **UI Components & Styling**:
  - Bootstrap Icons for consistent iconography
  - Select2 with Bootstrap 5 theme for enhanced form controls
  - Custom CSS following BEM methodology
  - Responsive design with mobile-first approach

- **JavaScript Architecture**:
  - ES6 modules for code organization
  - Service classes for API interaction
  - Utils for common functionality
  - Progressive enhancement pattern

- **Third-Party Integrations**:
  - [Google Maps JavaScript API](https://developers.google.com/maps/documentation/javascript/) for location services
  - [Chart.js](https://www.chartjs.org/) for data visualization
  - [Prettier](https://prettier.io/) for HTML formatting
  - [ESLint](https://eslint.org/) for JavaScript linting

### AWS Lambda Integration

- **Runtime**: Python 3.13
- **WSGI Adapter**: AWS-wsgi
- **Handler**: Lambda-compatible entry point
- **Layers**: Custom runtime dependencies
- **Environment**: Configuration via Lambda environment variables
- **Logging**: Structured JSON logging with CloudWatch

## Infrastructure

### AWS Services

- **Compute**: AWS Lambda
- **API**: API Gateway HTTP API
- **Storage**:
  - S3 for Lambda deployment packages
  - RDS PostgreSQL for data storage
- **Networking**:
  - VPC with public/private subnets
  - Security Groups for access control
  - NAT Gateway for outbound internet access
- **Secrets**: AWS Secrets Manager for credentials
- **Monitoring**:
  - CloudWatch Logs
  - CloudWatch Metrics
  - CloudWatch Alarms

### Local Development

- LocalStack for AWS service emulation
- Docker Compose for local services
- SQLite for local development database

## CI/CD Pipeline

### GitHub Actions Workflows

1. **PR Validation**

- Code linting (Python, Terraform)
  - Unit and integration tests
  - Security scanning (Trivy, Bandit)
  - Terraform plan validation
  - Test coverage reporting

1. **Deployment**

- Build and package Flask application
  - Upload deployment package to S3
  - Update Lambda function
  - Run database migrations
  - Update API Gateway configuration
  - Run integration tests
  - Notify on success/failure

1. **Environment Promotion**

- Manual approval gates
  - Environment-specific configuration
  - Zero-downtime deployments
  - Automated rollback on failure

1. **Infrastructure**

- Terraform plan/apply
  - Drift detection
  - Cost estimation
  - Security scanning

## Development Tools

### Local Development

- **Development Environment**: Make-based workflow with comprehensive targets
  - `make setup` - Automated development environment setup
  - `make run` - Start Flask development server
  - `make test` - Run test suite with coverage
  - `make lint` - Run all linters and formatters

- **Containerization**: Docker Compose for local services
  - PostgreSQL container for local database
  - LocalStack for AWS service emulation (when needed)
  - Development-focused container setup

- **Dependency Management**: pip-tools with structured requirements
  - `requirements/base.in` - Core dependencies
  - `requirements/dev.in` - Development tools
  - `requirements/test.in` - Testing dependencies
  - `requirements/prod.in` - Production-specific packages

### Code Quality & Linting

- **Python**:
  - [Flake8](https://flake8.pycqa.org/) - Style and complexity linting
  - [Black](https://black.readthedocs.io/) - Code formatting (120 char line length)
  - [isort](https://pycqa.github.io/isort/) - Import sorting
  - [Mypy](https://mypy.readthedocs.io/) - Static type checking
  - [Bandit](https://bandit.readthedocs.io/) - Security vulnerability scanning

- **Frontend**:
  - [ESLint 9.34.0](https://eslint.org/) - JavaScript linting with flat config
  - [Prettier 3.2.4](https://prettier.io/) - HTML template formatting
  - Environment-specific rules (development vs production)

- **Infrastructure**:
  - [TFLint](https://github.com/terraform-linters/tflint) - Terraform linting
  - [ShellCheck](https://www.shellcheck.net/) - Shell script analysis
  - [yamllint](https://yamllint.readthedocs.io/) - YAML file validation

- **Security Scanning**:
  - [Trivy](https://trivy.dev/) - Dependency and container vulnerability scanning
  - [GitLeaks](https://github.com/gitleaks/gitleaks) - Secret detection
  - Pre-commit hooks for automated quality checks

### AWS Development

- **AWS SAM CLI** for local Lambda testing
- **AWS CLI** for service interaction
- **AWS Vault** for credential management
- **LocalStack** for offline development

### Testing

- **Unit/Integration**:
- pytest (Python)

- **Coverage**:
  - pytest-cov
  - Codecov integration
  - Minimum coverage requirements

### Documentation

- **API**:
- Swagger/OpenAPI
- Interactive API documentation
- Request/response examples

- **Architecture**:

  - C4 Model
  - System context diagrams
  - Component diagrams

- **Decisions**:
  - ADRs (Architecture Decision Records)
  - RFCs for major changes
  - Design documents

### Version Control

- **Hosting**: GitHub
- Code hosting
- Issue tracking
- Project management

- **Branching Strategy**:

  - GitHub Flow
  - Feature branches
  - Protected main branch

- **PR Process**:
  - Required code reviews
  - Status checks
  - Automated testing
  - Code coverage requirements

## Deployment

### Environments

- **Development**
- Local development
- Feature environments (per-PR)
- Cloud-based development

- **Staging**

  - Mirrors production
  - Integration testing
  - Performance testing

- **Production**
  - Production environment
  - Blue/green deployment
  - Canary releases (future)

### Deployment Process

1. **Code Review**

- Pull request creation
  - Automated checks
  - Code review approval

1. **Testing**

- Unit tests
  - Integration tests
  - Security scans

1. **Staging Deployment**

- Terraform plan review
  - Automated deployment
  - Smoke tests
  - Integration verification

1. **Verification**

- Manual testing
  - Stakeholder review
  - Performance validation

1. **Production Deployment**

- Change approval
  - Automated deployment
  - Health checks
  - Monitoring verification

1. **Post-Deployment**

- Smoke tests
  - Monitoring setup
  - Rollback plan
  - Documentation update

## Monitoring and Operations

### Logging

- AWS CloudWatch Logs
- Centralized log collection
- Log groups and streams
- Retention policies
- **Log Retention**
  - Development: 7 days
  - Staging: 30 days
  - Production: 1 year

### Metrics

- **Application Metrics**
- Request/response times
- Error rates
- Business metrics
- Custom CloudWatch metrics

- **Infrastructure Metrics**

  - CPU/Memory usage
  - Disk I/O
  - Network throughput
  - Database performance

- **Business Metrics**
  - User activity
  - Feature usage
  - Conversion rates

### Alerting

- **Critical Alerts**
- PagerDuty integration
- 24/7 on-call rotation
- Escalation policies

- **Non-critical Alerts**

  - Email notifications
  - Slack channels
  - Daily digest

- **Alert Thresholds**
  - Warning levels
  - Critical levels
  - Auto-remediation (where possible)

## Security

### Data Protection

- **Encryption at REST**
- AWS KMS for encryption
- EBS volume encryption
- S3 server-side encryption
- RDS encryption

- **Encryption in Transit**

  - TLS 1.2+ required
  - HSTS headers
  - Certificate management
  - Perfect Forward Secrecy

- **Secrets Management**
  - AWS Secrets Manager
  - Environment variables
  - Secret rotation
  - Access logging

### Access Control

- **AWS IAM**
- Least privilege principle
- Role-based access
- Temporary credentials
- Multi-factor authentication

- **Application RBAC**
  - Role definitions
  - Permission scopes
  - Audit logging
  - Session management

### Compliance

- **Standards**
- AWS Well-Architected Framework
- OWASP Top 10
- CIS Benchmarks
- GDPR compliance

- **Auditing**
  - AWS Config rules
  - CloudTrail logging
  - Regular security assessments
  - Penetration testing

---

_Last Updated: January 2025_  
_Reflects Current Technology Implementation_
