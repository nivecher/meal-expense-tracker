# =============================================================================
# Meal Expense Tracker - Makefile
# =============================================================================
#
# Available commands (run 'make help' for details):
#   Development:   setup, run, test, lint, format, check, pre-commit
#   Database:      db-{init,migrate,upgrade,downgrade}
#   Docker:        docker-{up,down,logs,shell,rebuild}
#   Testing:       test, test-unit, test-integration, test-smoke
#   Terraform:     tf-{init,plan,apply,destroy,validate}
#   Deployment:    deploy-{dev,staging,prod}
#   Utilities:     help, clean, distclean, check-env
# =============================================================================

# =============================================================================
# Configuration
# =============================================================================

# Application settings
APP_NAME = meal-expense-tracker
DOCKER_PORT = 8000
PYTHON = ./venv/bin/python3
PIP = ./venv/bin/pip3

# Parallel execution safety for critical operations
.NOTPARALLEL: docker-rebuild tf-apply tf-destroy deploy-prod deploy-staging

# Python settings
PYTHONPATH = $(shell pwd)
PYTEST_OPTS = -v --cov=app --cov-report=term-missing --cov-report=html
PYTEST_PARALLEL = -n auto
TEST_PATH = tests/

# Docker settings
DOCKER_COMPOSE = docker-compose -f docker-compose.yml
DOCKER_COMPOSE_DEV = $(DOCKER_COMPOSE) -f docker-compose.dev.yml
CONTAINER_NAME = $(APP_NAME)-app
IMAGE_NAME = $(APP_NAME)
VOLUME_NAME = $(APP_NAME)-db
TARGET_PLATFORM ?= linux/arm64

# Terraform settings
ENV ?= dev
TF_ENV ?= $(ENV)
TF_ROOT := $(shell pwd)/terraform
TF_ENV_DIR = $(TF_ROOT)/environments/$(TF_ENV)
TF_BACKEND_CONFIG = $(TF_ENV_DIR)/backend.hcl
TF_PARALLELISM ?= 30
TF_ARGS ?= -parallelism=$(TF_PARALLELISM) -refresh=true

# Pipeline settings
SKIP_TESTS ?= false
TAG ?= v1.0.0

# AWS settings
DEFAULT_AWS_PROFILE ?= default
DEFAULT_AWS_REGION ?= us-east-1
LAMBDA_FUNCTION_NAME ?= meal-expense-tracker-$(TF_ENV)

# Enable BuildKit for better build performance
export DOCKER_BUILDKIT=1
export COMPOSE_DOCKER_CLI_BUILD=1
export PYTHONPATH

# =============================================================================
# Help
# =============================================================================

## Display help message
.PHONY: help
help:  ## Show this help message
	@echo "\n\033[1mMeal Expense Tracker - Available Commands\033[0m\n"
	@echo "\033[1mDevelopment:\033[0m"
	@echo "  \033[1mmake setup\033[0m           Complete development environment setup"
	@echo "  \033[1mmake setup-quick\033[0m     Quick development setup (minimal)"
	@echo "  \033[1mmake setup-optional\033[0m  Install optional development tools"
	@echo "  \033[1mmake upgrade-tools\033[0m   Upgrade all development tools"
	@echo "  \033[1mmake reset-dev\033[0m       Reset development environment"
	@echo "  \033[1mmake dev-status\033[0m      Check development environment status"
	@echo "  \033[1mmake run\033[0m             Run the application locally"
	@echo ""
	@echo "\033[1mTool Upgrades:\033[0m"
	@echo "  \033[1mmake upgrade-node\033[0m      Upgrade Node.js to latest version"
	@echo "  \033[1mmake upgrade-python\033[0m    Upgrade Python to latest version"
	@echo "  \033[1mmake upgrade-docker\033[0m    Upgrade Docker to latest version"
	@echo "  \033[1mmake upgrade-terraform\033[0m Upgrade Terraform to latest version"
	@echo "  \033[1mmake upgrade-aws\033[0m       Upgrade AWS CLI to latest version"
	@echo "  \033[1mmake upgrade-act\033[0m       Upgrade act to latest version"
	@echo "  \033[1mmake upgrade-playwright\033[0m Upgrade Playwright to latest version"
	@echo "  \033[1mmake format\033[0m          Format code (Python, HTML, CSS, JS)"
	@echo "  \033[1mmake lint\033[0m            Run linters (Python, HTML, CSS, JS)"
	@echo "  \033[1mmake lint-fix\033[0m        Run linters with auto-fix (Python, HTML, CSS, JS)"
	@echo "  \033[1mmake test\033[0m            Run all tests with coverage"
	@echo "  \033[1mmake check\033[0m           Run all checks (format + lint + test)"
	@echo "  \033[1mmake check-fix\033[0m       Run all checks with auto-fix (format + lint-fix + test)"
	@echo "  \033[1mmake pre-commit\033[0m      Run pre-commit checks"
	@echo "  \033[1mmake validate-env\033[0m    Validate development environment"

	@echo "\n\033[1mLocal CI/CD:\033[0m"
	@echo "  \033[1mmake ci-local\033[0m        Run local CI workflow (equivalent to ci.yml)"
	@echo "  \033[1mmake ci-quick\033[0m        Run quick CI checks (lint + unit tests)"
	@echo "  \033[1mmake pipeline-local\033[0m  Run local pipeline workflow (equivalent to deploy.yml)"
	@echo "  \033[1mmake act-setup\033[0m       Setup act configuration files"
	@echo "  \033[1mmake act-ci\033[0m          Run complete CI workflow"
	@echo "  \033[1mmake act-pipeline\033[0m    Run complete pipeline workflow"
	@echo "  \033[1mmake act-lint\033[0m        Run linting job only"
	@echo "  \033[1mmake act-test\033[0m        Run test jobs only"
	@echo "  \033[1mmake act-security\033[0m    Run security scan only"
	@echo "  \033[1mmake act-help\033[0m        Show all act commands and examples"

	@echo "\n\033[1mDatabase:\033[0m"
	@echo "  \033[1mmake db-init\033[0m         Initialize database"
	@echo "  \033[1mmake db-migrate\033[0m      Create new database migration"
	@echo "  \033[1mmake db-upgrade\033[0m      Upgrade database to latest migration"
	@echo "  \033[1mmake db-downgrade\033[0m    Downgrade database by one migration"

	@echo "\n\033[1mDocker:\033[0m"
	@echo "  \033[1mmake docker-up\033[0m       Start all containers in detached mode"
	@echo "  \033[1mmake docker-down\033[0m     Stop and remove all containers"
	@echo "  \033[1mmake docker-logs\033[0m     View container logs (follow mode)"
	@echo "  \033[1mmake docker-shell\033[0m    Open shell in the application container"
	@echo "  \033[1mmake docker-rebuild\033[0m  Rebuild and restart containers"
	@echo "  \033[1mmake docker-build-fast\033[0m ⚡ Fast Docker build (production deps only)"
	@echo "  \033[1mmake docker-build-standard\033[0m 🚀 Standard Docker build (optimized by default)"

	@echo "\n\033[1mTesting:\033[0m"
	@echo "  \033[1mmake test\033[0m            Run all tests with coverage"
	@echo "  \033[1mmake test-unit\033[0m        Run only unit tests"
	@echo "  \033[1mmake test-integration\033[0m Run only integration tests"
	@echo "  \033[1mmake test-smoke\033[0m       Run smoke tests"
	@echo "  \033[1mmake test-frontend\033[0m    Run Playwright frontend tests"
	@echo "  \033[1mmake test-user-flows\033[0m  Run Playwright user flow/usability tests"
	@echo "  \033[1mmake test-security\033[0m    Run security headers tests"
	@echo "  \033[1mmake test-console\033[0m     Run console error tests"
	@echo "  \033[1mmake test-e2e\033[0m         Run all end-to-end tests"
	@echo "  \033[1mmake test-frontend-headed\033[0m Run frontend tests with browser visible"
	@echo "  \033[1mmake test-user-flows-headed\033[0m Run user flow tests with browser visible"
	@echo "  \033[1mmake test-frontend-debug\033[0m Run frontend tests in debug mode"
	@echo "  \033[1mmake test-report\033[0m      Generate HTML test report"
	@echo "  \033[1mmake install-playwright\033[0m Install Playwright dependencies"

	@echo "\n\033[1mTerraform (TF_ENV=env, default: dev):\033[0m"
	@echo "  \033[1mmake tf-init\033[0m        Initialize Terraform with backend config"
	@echo "  \033[1mmake tf-plan\033[0m        Generate and show execution plan"
	@echo "  \033[1mmake tf-apply\033[0m       Apply changes to infrastructure"
	@echo "  \033[1mmake tf-destroy\033[0m     Destroy infrastructure"
	@echo "  \033[1mmake tf-validate\033[0m    Validate Terraform configuration"

	@echo "\n\033[1mDeployment Pipeline:\033[0m"
	@echo "  \033[1mmake package\033[0m         ⚡ Lambda package (app only)"
	@echo "  \033[1mmake package-layer\033[0m   ⚡ Lambda layer (architecture-aware)"
	@echo "  \033[1mmake package-complete\033[0m ⚡ Complete package (app + layer)"
	@echo "  \033[1mmake deploy-dev\033[0m      Deploy to development environment"
	@echo "  \033[1mmake deploy-staging\033[0m  Deploy to staging environment"
	@echo "  \033[1mmake deploy-prod\033[0m     Deploy to production environment"
	@echo "  \033[1mmake release-staging\033[0m Release to staging (tag-based)"
	@echo "  \033[1mmake release-prod\033[0m    Release to production (tag-based)"

	@echo "\n\033[1mRequirements & Security:\033[0m"
	@echo "  \033[1mmake requirements\033[0m     Generate requirements files from .in files"
	@echo "  \033[1mmake security-check\033[0m   Run security checks (vulnerabilities + bandit)"
	@echo "  \033[1mmake security-vulns\033[0m    Check for known vulnerabilities"
	@echo "  \033[1mmake security-bandit\033[0m   Run Bandit security linter"
	@echo "  \033[1mmake deps-check\033[0m        Check for outdated dependencies"
	@echo "  \033[1mmake deps-update\033[0m       Update dependencies to latest versions"

	@echo "\n\033[1mUtilities:\033[0m"
	@echo "  \033[1mmake clean\033[0m           Remove build artifacts and temporary files"
	@echo "  \033[1mmake distclean\033[0m        Remove all generated files including virtual environment"
	@echo "  \033[1mmake check-env\033[0m        Check development environment setup"

	@echo "\n\033[1mExamples:\033[0m"
	@echo "  \033[1mmake validate-env && make setup && make run\033[0m  # Safe setup and run"
	@echo "  \033[1mmake check\033[0m                                 # Run all quality checks"
	@echo "  \033[1mmake tf-plan\033[0m                               # Plan Terraform changes"

# =============================================================================
# Virtual Environment
# =============================================================================

## Create and activate Python virtual environment
.PHONY: venv
venv:
	@if [ ! -d "venv" ]; then \
		echo "Creating virtual environment..."; \
		python3 -m venv venv; \
		echo "Virtual environment created. Run 'source venv/bin/activate' to activate."; \
	else \
		echo "Virtual environment already exists. Run 'source venv/bin/activate' to activate."; \
	fi

# =============================================================================
# Development
# =============================================================================

## Complete development environment setup
.PHONY: setup
setup:
	@echo "\n\033[1m=== Running Development Setup ===\033[0m"
	@./scripts/setup-dev.sh --mode full
	@echo "\n\033[1mNext steps:\033[0m"
	@echo "  \033[1msource venv/bin/activate\033[0m  # Activate virtual environment"
	@echo "  \033[1mmake run\033[0m                 # Start the application"
	@echo "  \033[1mmake test\033[0m                # Run tests"
	@echo "  \033[1mmake security-check\033[0m       # Check security"

## Run the application locally
.PHONY: run
run: check-env
	$(PYTHON) -m flask run

## Run all linters
.PHONY: lint
lint: lint-python lint-mypy lint-html lint-css lint-js lint-markdown lint-yaml lint-json lint-toml lint-terraform-fmt

## Run all linters with auto-fix
.PHONY: lint-fix
lint-fix: lint-python-fix lint-html-fix lint-css-fix lint-js-fix

## Python linter
.PHONY: lint-python
lint-python: check-env
	@echo "\n\033[1m=== Running Python Linter ===\033[0m"
	@$(PYTHON) -m ruff check app tests || (echo "\033[1;31m❌ Ruff failed\033[0m"; exit 1)
	@$(PYTHON) -m black --check app tests || (echo "\033[1;31m❌ Black check failed\033[0m"; exit 1)

## Python type checker
.PHONY: lint-mypy
lint-mypy: check-env
	@echo "\n\033[1m=== Running MyPy Type Checker ===\033[0m"
	@$(PYTHON) -m mypy app --config-file=pyproject.toml || (echo "\033[1;31m❌ MyPy failed\033[0m"; exit 1)

## Format all code (Python, HTML, CSS, JS)
.PHONY: format
format: format-python format-html format-css format-js

## Format Python code
.PHONY: format-python
format-python: check-env
	@echo "\n\033[1m=== Formatting Python code ===\033[0m"
	@$(PYTHON) -m ruff check --fix app/ tests/ migrations/ || (echo "\033[1;31m❌ Ruff check --fix failed\033[0m"; exit 1)
	@$(PYTHON) -m black app/ tests/ migrations/ */*.py *.py || (echo "\033[1;31m❌ black failed\033[0m"; exit 1)

## HTML linter
.PHONY: lint-html
lint-html: check-npm
	@echo "\n\033[1m=== Running HTML Linter ===\033[0m"
	@npm run lint-html 2>/dev/null | grep -v "unchanged" || (echo "\033[1;31m❌ HTML linting failed\033[0m"; exit 1)

## CSS linter
.PHONY: lint-css
lint-css: check-npm
	@echo "\n\033[1m=== Running CSS Linter ===\033[0m"
	@npm run lint:css 2>/dev/null || (echo "\033[1;31m❌ CSS linting failed\033[0m"; exit 1)

## JavaScript linter
.PHONY: lint-js
lint-js: check-npm
	@echo "\n\033[1m=== Running JavaScript Linter ===\033[0m"
	@npm run lint:js 2>/dev/null || (echo "\033[1;31m❌ JavaScript linting failed\033[0m"; exit 1)

## Markdown linter
.PHONY: lint-markdown
lint-markdown: check-npm
	@echo "\n\033[1m=== Running Markdown Linter ===\033[0m"
	@if command -v markdownlint >/dev/null 2>&1; then \
		markdownlint --config .markdownlint.json "**/*.md" || (echo "\033[1;31m❌ Markdown linting failed\033[0m"; exit 1); \
	else \
		echo "\033[1;33m⚠️  markdownlint-cli not installed. Install with: npm install -g markdownlint-cli\033[0m"; \
		exit 1; \
	fi

## YAML linter (formatting check with Prettier)
.PHONY: lint-yaml
lint-yaml: check-npm
	@echo "\n\033[1m=== Running YAML Format Check ===\033[0m"
	@find . -type f \( -name "*.yaml" -o -name "*.yml" \) ! -path "./venv/*" ! -path "./node_modules/*" ! -path "./.git/*" ! -path "./cloudformation/*" -exec npx --yes prettier --check {} + || (echo "\033[1;31m❌ YAML formatting check failed\033[0m"; exit 1)

## JSON linter
.PHONY: lint-json
lint-json: check-npm
	@echo "\n\033[1m=== Running JSON Linter ===\033[0m"
	@npx --yes prettier --check "**/*.json" || (echo "\033[1;31m❌ JSON validation failed\033[0m"; exit 1)

## TOML linter
.PHONY: lint-toml
lint-toml: check-env
	@echo "\n\033[1m=== Running TOML Linter ===\033[0m"
	@$(PYTHON) -c "import tomllib; import glob; [tomllib.loads(open(f, 'r').read()) for f in glob.glob('**/*.toml', recursive=True) if not any(x in f for x in ['venv', 'node_modules', '.git'])]" 2>/dev/null || (echo "\033[1;31m❌ TOML validation failed\033[0m"; exit 1)

## Terraform formatter check
.PHONY: lint-terraform-fmt
lint-terraform-fmt:
	@echo "\n\033[1m=== Running Terraform Format Check ===\033[0m"
	@if command -v terraform >/dev/null 2>&1; then \
		if [ -d "terraform" ]; then \
			terraform -chdir=terraform fmt -check -recursive || (echo "\033[1;31m❌ Terraform formatting check failed\033[0m"; exit 1); \
		else \
			echo "\033[1;33m⚠️  No terraform directory found, skipping\033[0m"; \
		fi; \
	else \
		echo "\033[1;33m⚠️  Terraform not installed. Skipping format check\033[0m"; \
	fi

## Python linter with auto-fix
.PHONY: lint-python-fix
lint-python-fix: check-env
	@echo "\n\033[1m=== Running Python Linter with Auto-fix ===\033[0m"
	@$(PYTHON) -m ruff check --fix app tests || (echo "\033[1;31m❌ Ruff auto-fix failed\033[0m"; exit 1)
	@$(PYTHON) -m black app tests || (echo "\033[1;31m❌ Black auto-fix failed\033[0m"; exit 1)
	@$(PYTHON) -m ruff check app tests || (echo "\033[1;31m❌ Ruff check failed\033[0m"; exit 1)

## HTML linter with auto-fix
.PHONY: lint-html-fix
lint-html-fix: check-npm
	@echo "\n\033[1m=== Running HTML Linter with Auto-fix ===\033[0m"
	@npm run format-html 2>/dev/null | grep -v "unchanged" || (echo "\033[1;31m❌ HTML auto-fix failed\033[0m"; exit 1)

## CSS linter with auto-fix
.PHONY: lint-css-fix
lint-css-fix: check-npm
	@echo "\n\033[1m=== Running CSS Linter with Auto-fix ===\033[0m"
	@npm run format:css 2>/dev/null || (echo "\033[1;31m❌ CSS auto-fix failed\033[0m"; exit 1)

## JavaScript linter with auto-fix
.PHONY: lint-js-fix
lint-js-fix: check-npm
	@echo "\n\033[1m=== Running JavaScript Linter with Auto-fix ===\033[0m"
	@npm run format:js 2>/dev/null || (echo "\033[1;31m❌ JavaScript auto-fix failed\033[0m"; exit 1)

## Format HTML code
.PHONY: format-html
format-html: check-npm
	@echo "\n\033[1m=== Formatting HTML code ===\033[0m"
	@npm run format-html 2>/dev/null | grep -v "unchanged" || true

## Format CSS code
.PHONY: format-css
format-css: check-npm
	@echo "\n\033[1m=== Formatting CSS code ===\033[0m"
	@npm run format:css 2>/dev/null | grep -v "unchanged" || true

## Format JavaScript code
.PHONY: format-js
format-js: check-npm
	@echo "\n\033[1m=== Formatting JavaScript code ===\033[0m"
	@npm run format:js 2>/dev/null || (echo "\033[1;31m❌ JavaScript formatting failed\033[0m"; exit 1)

## Run all tests
.PHONY: test
test: check-env
	@echo "\n\033[1m=== Running Tests ===\033[0m"
	PYTHONPATH=. $(PYTHON) -m pytest tests/ $(PYTEST_OPTS) || (echo "\033[1;31m❌ Tests failed\033[0m"; exit 1)

## Validate linting synchronization
.PHONY: validate-linting-sync
validate-linting-sync:
	@echo "\n\033[1m=== Validating Linting Synchronization ===\033[0m"
	@./scripts/validate-linting-sync.sh

## Run pre-commit checks
.PHONY: pre-commit
pre-commit: format lint test

## Run all checks (format + lint + test)
.PHONY: check
check: format lint test

## Run all checks with auto-fix (format + lint-fix + test)
.PHONY: check-fix
check-fix: format lint-fix test

# =============================================================================
# Requirements Management & SCA
# =============================================================================

## Generate requirements files from .in files
.PHONY: requirements
requirements: requirements-prod requirements-dev
	@echo "\033[1;32m✅ Requirements files generated\033[0m"

## Generate production requirements
.PHONY: requirements-prod
requirements-prod: check-pip-tools
	@echo "\n\033[1m=== Generating Production Requirements ===\033[0m"
	@pip-compile --upgrade --constraint=constraints.txt requirements/base.in -o requirements.txt
	@echo "\033[1;32m✅ Production requirements generated\033[0m"

## Generate development requirements (includes security tools)
.PHONY: requirements-dev
requirements-dev: check-pip-tools
	@echo "\n\033[1m=== Generating Development Requirements ===\033[0m"
	@pip-compile --upgrade --constraint=constraints.txt requirements/dev.in -o requirements-dev.txt
	@echo "\033[1;32m✅ Development requirements generated\033[0m"

## Check if pip-tools is installed
.PHONY: check-pip-tools
check-pip-tools:
	@if ! $(PIP) show pip-tools >/dev/null 2>&1; then \
		echo "\033[1;33m⚠️  Installing pip-tools...\033[0m"; \
		$(PIP) install pip-tools; \
	fi

## Run security checks (vulnerabilities + bandit)
.PHONY: security-check
security-check: security-vulns security-bandit
	@echo "\n\033[1;32m✅ Security checks completed\033[0m"

## Run comprehensive security analysis (alias for security-check)
.PHONY: security-scan
security-scan: security-check

## Check for known vulnerabilities
.PHONY: security-vulns
security-vulns: check-env
	@echo "\n\033[1m=== Checking for Known Vulnerabilities ===\033[0m"
	@if ! $(PYTHON) -m safety --version >/dev/null 2>&1; then \
		echo "\033[1;33m⚠️  Installing safety...\033[0m"; \
		$(PIP) install safety; \
	fi
	@echo "\n\033[1m🔍 Scanning dependencies...\033[0m"
	@$(PYTHON) -m safety scan || true
	@echo "\033[1;32m✅ Vulnerability scan completed\033[0m"

## Run Bandit security linter
.PHONY: security-bandit
security-bandit: check-env
	@echo "\n\033[1m=== Running Bandit Security Linter ===\033[0m"
	@if ! $(PYTHON) -m bandit --version >/dev/null 2>&1; then \
		echo "\033[1;33m⚠️  Installing bandit...\033[0m"; \
		$(PIP) install bandit; \
	fi
	@$(PYTHON) -m bandit -c .bandit -r app/ || true
	@echo "\033[1;32m✅ Bandit security scan completed\033[0m"

## Check for outdated dependencies
.PHONY: deps-check
deps-check: check-env
	@echo "\n\033[1m=== Checking for Outdated Dependencies ===\033[0m"
	@$(PIP) list --outdated || echo "✅ All dependencies are up to date"

## Update dependencies
.PHONY: deps-update
deps-update: check-env
	@echo "\n\033[1m=== Updating Dependencies ===\033[0m"
	@$(MAKE) requirements
	@$(PIP) install --upgrade -r requirements.txt
	@$(PIP) install --upgrade -r requirements-dev.txt
	@echo "\033[1;32m✅ Dependencies updated\033[0m"

## Install production dependencies
.PHONY: install-deps
install-deps: check-env
	@echo "\n\033[1m=== Installing Production Dependencies ===\033[0m"
	@$(PIP) install -r requirements.txt
	@echo "\033[1;32m✅ Production dependencies installed\033[0m"

## Install development dependencies (includes security tools)
.PHONY: install-dev-deps
install-dev-deps: check-env
	@echo "\n\033[1m=== Installing Development Dependencies ===\033[0m"
	@$(PIP) install -r requirements-dev.txt
	@echo "\033[1;32m✅ Development dependencies installed\033[0m"

## Setup database for development
.PHONY: setup-db
setup-db: check-env
	@echo "\n\033[1m=== Setting up Development Database ===\033[0m"
	@$(PYTHON) -m flask db upgrade || echo "\033[1;33m⚠️  Database migration skipped (no database configured)\033[0m"
	@echo "\033[1;32m✅ Database setup complete\033[0m"

## Quick development setup (minimal)
.PHONY: setup-quick
setup-quick:
	@echo "\n\033[1m=== Running Quick Development Setup ===\033[0m"
	@./scripts/setup-dev.sh --mode minimal
	@echo "\n\033[1mNote:\033[0m Run \033[1mmake setup\033[0m for full setup including database"

## Install optional development tools
.PHONY: setup-optional
setup-optional:
	@echo "\n\033[1m=== Installing Optional Development Tools ===\033[0m"
	@./scripts/setup-dev.sh --mode optional
	@echo "\n\033[1;32m✅ Optional tools installation complete\033[0m"

## Upgrade all development tools
.PHONY: upgrade-tools
upgrade-tools:
	@echo "\n\033[1m=== Upgrading Development Tools ===\033[0m"
	@./scripts/setup-dev.sh --mode upgrade
	@echo "\n\033[1;32m✅ Tool upgrades complete\033[0m"

## Upgrade Node.js to latest version
.PHONY: upgrade-node
upgrade-node:
	@echo "\n\033[1m=== Upgrading Node.js ===\033[0m"
	@./scripts/setup-dev.sh --mode upgrade --tool node
	@echo "\n\033[1;32m✅ Node.js upgrade complete\033[0m"

## Upgrade Python to latest version
.PHONY: upgrade-python
upgrade-python:
	@echo "\n\033[1m=== Upgrading Python ===\033[0m"
	@./scripts/setup-dev.sh --mode upgrade --tool python
	@echo "\n\033[1;32m✅ Python upgrade complete\033[0m"

## Upgrade Docker to latest version
.PHONY: upgrade-docker
upgrade-docker:
	@echo "\n\033[1m=== Upgrading Docker ===\033[0m"
	@./scripts/setup-dev.sh --mode upgrade --tool docker
	@echo "\n\033[1;32m✅ Docker upgrade complete\033[0m"

## Upgrade Terraform to latest version
.PHONY: upgrade-terraform
upgrade-terraform:
	@echo "\n\033[1m=== Upgrading Terraform ===\033[0m"
	@./scripts/setup-dev.sh --mode upgrade --tool terraform
	@echo "\n\033[1;32m✅ Terraform upgrade complete\033[0m"

## Upgrade AWS CLI to latest version
.PHONY: upgrade-aws
upgrade-aws:
	@echo "\n\033[1m=== Upgrading AWS CLI ===\033[0m"
	@./scripts/setup-dev.sh --mode upgrade --tool aws
	@echo "\n\033[1;32m✅ AWS CLI upgrade complete\033[0m"

## Upgrade act to latest version
.PHONY: upgrade-act
upgrade-act:
	@echo "\n\033[1m=== Upgrading act ===\033[0m"
	@./scripts/setup-dev.sh --mode upgrade --tool act
	@echo "\n\033[1;32m✅ act upgrade complete\033[0m"

## Upgrade Playwright to latest version
.PHONY: upgrade-playwright
upgrade-playwright:
	@echo "\n\033[1m=== Upgrading Playwright ===\033[0m"
	@./scripts/setup-dev.sh --mode upgrade --tool playwright
	@echo "\n\033[1;32m✅ Playwright upgrade complete\033[0m"

## Reset development environment
.PHONY: reset-dev
reset-dev: clean-venv setup
	@echo "\n\033[1;32m✅ Development environment reset complete\033[0m"

## Check development environment status
.PHONY: dev-status
dev-status:
	@echo "\n\033[1m=== Development Environment Status ===\033[0m"
	@./scripts/setup-dev.sh --mode debug

# =============================================================================
# Local CI/CD Workflows
# =============================================================================

## Run local CI workflow (equivalent to ci.yml)
.PHONY: ci-local
ci-local: check-env
	@echo "\n\033[1m=== Running Local CI Workflow ===\033[0m"
	@./scripts/local-ci.sh

## Run quick CI checks (lint + unit tests)
.PHONY: ci-quick
ci-quick: check-env check-npm
	@echo "\n\033[1m=== Running Quick CI Checks ===\033[0m"
	@$(PYTHON) -m ruff check app tests || (echo "\033[1;31m❌ Ruff failed\033[0m"; exit 1)
	@$(PYTHON) -m black --check app tests || (echo "\033[1;31m❌ Black check failed\033[0m"; exit 1)
	@npm run lint-html || (echo "\033[1;31m❌ HTML linting failed\033[0m"; exit 1)
	@npm run lint:css || (echo "\033[1;31m❌ CSS linting failed\033[0m"; exit 1)
	@npm run lint:js || (echo "\033[1;31m❌ JavaScript linting failed\033[0m"; exit 1)
	@PYTHONPATH=. $(PYTHON) -m pytest tests/unit/ $(PYTEST_OPTS) || (echo "\033[1;31m❌ Unit tests failed\033[0m"; exit 1)
	@echo "\033[1;32m✅ Quick CI checks completed\033[0m"

## Run local pipeline workflow (equivalent to deploy.yml)
.PHONY: pipeline-local
pipeline-local: check-env
	@echo "\n\033[1m=== Running Local Deploy Workflow ===\033[0m"
	@./scripts/local-pipeline.sh $(ENV) $(SKIP_TESTS)

# Act Configuration
ACT_PLATFORM ?= ubuntu-latest=catthehacker/ubuntu:act-latest
ACT_SECRET_FILE ?= .secrets
ACT_ENV_FILE ?= .env.act
ACT_ARTIFACT_SERVER_PATH ?= /tmp/artifacts

## Check if act is installed
.PHONY: check-act
check-act:
	@if ! command -v act >/dev/null 2>&1; then \
		echo "\033[1;31m❌ act is not installed\033[0m"; \
		echo "\033[1;36mℹ️  Install act for local GitHub Actions testing:\033[0m"; \
		echo "  • macOS: brew install act"; \
		echo "  • Linux: curl -s https://raw.githubusercontent.com/nektos/act/master/install.sh | sudo bash"; \
		echo "  • Windows: choco install act-cli"; \
		echo "  • Or download from: https://github.com/nektos/act/releases"; \
		exit 1; \
	fi
	@echo "\033[1;32m✅ act is installed: $(shell act --version)\033[0m"

## Setup act configuration files
.PHONY: act-setup
act-setup: check-act
	@echo "\033[1m🔧 Setting up act configuration...\033[0m"
	@if [ ! -f ".actrc" ]; then \
		echo "Creating .actrc configuration..."; \
		echo "-P $(ACT_PLATFORM)" > .actrc; \
		echo "--artifact-server-path $(ACT_ARTIFACT_SERVER_PATH)" >> .actrc; \
		if [ -f "$(ACT_SECRET_FILE)" ]; then \
			echo "--secret-file $(ACT_SECRET_FILE)" >> .actrc; \
		fi; \
		if [ -f "$(ACT_ENV_FILE)" ]; then \
			echo "--env-file $(ACT_ENV_FILE)" >> .actrc; \
		fi; \
		echo "\033[1;32m✅ Created .actrc configuration\033[0m"; \
	else \
		echo "\033[1;33m⚠️  .actrc already exists\033[0m"; \
	fi
	@if [ ! -f "$(ACT_ENV_FILE)" ]; then \
		echo "Creating sample .env.act file..."; \
		echo "# Environment variables for act" > $(ACT_ENV_FILE); \
		echo "PYTHON_VERSION=3.13" >> $(ACT_ENV_FILE); \
		echo "NODE_VERSION=20" >> $(ACT_ENV_FILE); \
		echo "PYTHONPATH=/github/workspace" >> $(ACT_ENV_FILE); \
		echo "FLASK_ENV=test" >> $(ACT_ENV_FILE); \
		echo "TESTING=true" >> $(ACT_ENV_FILE); \
		echo "\033[1;32m✅ Created $(ACT_ENV_FILE) sample file\033[0m"; \
	fi
	@echo "\033[1;36mℹ️  Edit $(ACT_ENV_FILE) and $(ACT_SECRET_FILE) as needed\033[0m"

## Run CI workflow locally
.PHONY: act-ci
act-ci: check-act
	@echo "\033[1m🚀 Running CI workflow locally with act...\033[0m"
	act -W .github/workflows/ci.yml --artifact-server-path $(ACT_ARTIFACT_SERVER_PATH)

## Run pipeline workflow locally (if available)
.PHONY: act-pipeline
act-pipeline: check-act
	@if [ -f ".github/workflows/pipeline.yml" ]; then \
		echo "\033[1m🚀 Running pipeline workflow locally with act...\033[0m"; \
		act -W .github/workflows/pipeline.yml --artifact-server-path $(ACT_ARTIFACT_SERVER_PATH); \
	else \
		echo "\033[1;33m⚠️  Pipeline workflow not found, running CI workflow instead...\033[0m"; \
		act -W .github/workflows/ci.yml --artifact-server-path $(ACT_ARTIFACT_SERVER_PATH); \
	fi

## Run lint job locally
.PHONY: act-lint
act-lint: check-act
	@echo "\033[1m🔍 Running lint job locally with act...\033[0m"
	act -W .github/workflows/ci.yml -j lint --artifact-server-path $(ACT_ARTIFACT_SERVER_PATH)

## Run test jobs locally
.PHONY: act-test
act-test: check-act
	@echo "\033[1m🧪 Running test jobs locally with act...\033[0m"
	act -W .github/workflows/ci.yml -j test --artifact-server-path $(ACT_ARTIFACT_SERVER_PATH)

## Run security scan locally
.PHONY: act-security
act-security: check-act
	@echo "\033[1m🔒 Running security scan locally with act...\033[0m"
	act -W .github/workflows/ci.yml -j security --artifact-server-path $(ACT_ARTIFACT_SERVER_PATH)

## Run quality gate locally (CI workflow)
.PHONY: act-quality-gate
act-quality-gate: check-act
	@echo "\033[1m✅ Running quality gate locally with act...\033[0m"
	act -W .github/workflows/ci.yml --artifact-server-path $(ACT_ARTIFACT_SERVER_PATH)

## Run terraform validation locally
.PHONY: act-terraform
act-terraform: check-act
	@echo "\033[1m🏗️  Running terraform validation locally with act...\033[0m"
	act -W .github/workflows/ci.yml -j terraform --artifact-server-path $(ACT_ARTIFACT_SERVER_PATH)

## List available workflows and jobs
.PHONY: act-list
act-list: check-act
	@echo "\033[1m📋 Available workflows and jobs:\033[0m"
	@echo "\n\033[1mCI Workflow (.github/workflows/ci.yml):\033[0m"
	act -W .github/workflows/ci.yml --list
	@if [ -f ".github/workflows/pipeline.yml" ]; then \
		echo "\n\033[1mPipeline Workflow (.github/workflows/pipeline.yml):\033[0m"; \
		act -W .github/workflows/pipeline.yml --list; \
	else \
		echo "\n\033[1;33m⚠️  Pipeline workflow not found (using CI only)\033[0m"; \
	fi

## Run specific workflow with custom event
.PHONY: act-run
act-run: check-act
	@if [ -z "$(WORKFLOW)" ]; then \
		echo "\033[1;31m❌ WORKFLOW is required\033[0m"; \
		echo "Usage: make act-run WORKFLOW=ci [JOB=lint] [EVENT=push]"; \
		echo "Examples:"; \
		echo "  make act-run WORKFLOW=ci"; \
		echo "  make act-run WORKFLOW=ci JOB=lint"; \
		echo "  make act-run WORKFLOW=pipeline EVENT=workflow_dispatch"; \
		exit 1; \
	fi
	@echo "\033[1m🚀 Running workflow $(WORKFLOW) locally...\033[0m"
	@if [ -n "$(JOB)" ]; then \
		act $(or $(EVENT),push) -W .github/workflows/$(WORKFLOW).yml -j $(JOB) --artifact-server-path $(ACT_ARTIFACT_SERVER_PATH); \
	else \
		act $(or $(EVENT),push) -W .github/workflows/$(WORKFLOW).yml --artifact-server-path $(ACT_ARTIFACT_SERVER_PATH); \
	fi

## Run act with pull request event
.PHONY: act-pr
act-pr: check-act
	@echo "\033[1m🔄 Running workflows for pull_request event...\033[0m"
	act pull_request -W .github/workflows/ci.yml --artifact-server-path $(ACT_ARTIFACT_SERVER_PATH)

## Run act with workflow_dispatch event
.PHONY: act-dispatch
act-dispatch: check-act
	@echo "\033[1m⚡ Running workflows for workflow_dispatch event...\033[0m"
	@if [ -f ".github/workflows/pipeline.yml" ]; then \
		act workflow_dispatch -W .github/workflows/pipeline.yml --artifact-server-path $(ACT_ARTIFACT_SERVER_PATH); \
	else \
		echo "\033[1;33m⚠️  Pipeline workflow not found, using CI workflow...\033[0m"; \
		act workflow_dispatch -W .github/workflows/ci.yml --artifact-server-path $(ACT_ARTIFACT_SERVER_PATH); \
	fi

## Dry run workflows (plan only)
.PHONY: act-plan
act-plan: check-act
	@echo "\033[1m📋 Planning workflow execution (dry run)...\033[0m"
	@if [ -n "$(WORKFLOW)" ]; then \
		act -W .github/workflows/$(WORKFLOW).yml --dryrun; \
	else \
		echo "Planning CI workflow:"; \
		act -W .github/workflows/ci.yml --dryrun; \
		if [ -f ".github/workflows/pipeline.yml" ]; then \
			echo "\nPlanning Pipeline workflow:"; \
			act -W .github/workflows/pipeline.yml --dryrun; \
		fi; \
	fi

## Clean act artifacts and containers
.PHONY: act-clean
act-clean:
	@echo "\033[1m🧹 Cleaning act artifacts and containers...\033[0m"
	@rm -rf $(ACT_ARTIFACT_SERVER_PATH) 2>/dev/null || true
	@docker container prune -f --filter label=act 2>/dev/null || true
	@docker image prune -f --filter label=act 2>/dev/null || true
	@echo "\033[1;32m✅ Act cleanup completed\033[0m"

## Show act help and examples
.PHONY: act-help
act-help: check-act
	@echo "\033[1m🎯 Act Local Testing - Available Commands\033[0m"
	@echo ""
	@echo "\033[1mSetup:\033[0m"
	@echo "  \033[1mmake act-setup\033[0m          Setup act configuration files"
	@echo "  \033[1mmake check-act\033[0m          Verify act installation"
	@echo ""
	@echo "\033[1mWorkflow Testing:\033[0m"
	@echo "  \033[1mmake act-ci\033[0m             Run complete CI workflow"
	@echo "  \033[1mmake act-pipeline\033[0m       Run complete pipeline workflow"
	@echo "  \033[1mmake act-lint\033[0m           Run linting job only"
	@echo "  \033[1mmake act-test\033[0m           Run test jobs only"
	@echo "  \033[1mmake act-security\033[0m       Run security scan only"
	@echo "  \033[1mmake act-quality-gate\033[0m   Run quality gate only"
	@echo "  \033[1mmake act-terraform\033[0m      Run terraform validation only"
	@echo ""
	@echo "\033[1mAdvanced Usage:\033[0m"
	@echo "  \033[1mmake act-run WORKFLOW=ci JOB=lint\033[0m          Run specific job"
	@echo "  \033[1mmake act-pr\033[0m                                Run for PR event"
	@echo "  \033[1mmake act-dispatch\033[0m                          Run workflow_dispatch"
	@echo "  \033[1mmake act-plan\033[0m                              Dry run (plan only)"
	@echo "  \033[1mmake act-list\033[0m                              List all workflows/jobs"
	@echo ""
	@echo "\033[1mUtilities:\033[0m"
	@echo "  \033[1mmake act-clean\033[0m          Clean artifacts and containers"
	@echo "  \033[1mmake act-help\033[0m           Show this help"
	@echo ""
	@echo "\033[1mExamples:\033[0m"
	@echo "  \033[1mmake act-setup && make act-lint\033[0m                    # Setup and run linting"
	@echo "  \033[1mmake act-run WORKFLOW=ci JOB=test EVENT=pull_request\033[0m # Run tests for PR"
	@echo "  \033[1mmake act-plan WORKFLOW=pipeline\033[0m                     # Plan pipeline execution"
	@echo ""
	@echo "\033[1mConfiguration Files:\033[0m"
	@echo "  \033[1m.actrc\033[0m                  Act configuration file"
	@echo "  \033[1m.env.act\033[0m               Environment variables for act"
	@echo "  \033[1m.secrets\033[0m               Secrets file (create manually if needed)"

## Run unit tests only
.PHONY: test-unit
test-unit:
	@echo "\n\033[1m=== Running Unit Tests (Parallel) ===\033[0m"
	PYTHONPATH=. $(PYTHON) -m pytest tests/unit/ $(PYTEST_OPTS) $(PYTEST_PARALLEL) || (echo "\033[1;31m❌ Unit tests failed\033[0m"; exit 1)

## Run unit tests quickly (no coverage, parallel)
.PHONY: test-fast
test-fast:
	@echo "\n\033[1m=== Running Fast Unit Tests (Parallel, No Coverage) ===\033[0m"
	PYTHONPATH=. $(PYTHON) -m pytest tests/unit/ -q $(PYTEST_PARALLEL) || (echo "\033[1;31m❌ Unit tests failed\033[0m"; exit 1)

## Run integration tests only
.PHONY: test-integration
test-integration:
	@echo "\n\033[1m=== Running Integration Tests ===\033[0m"
	PYTHONPATH=. $(PYTHON) -m pytest tests/integration/ $(PYTEST_OPTS) || (echo "\033[1;31m❌ Integration tests failed\033[0m"; exit 1)

## Run smoke tests
.PHONY: test-smoke
test-smoke:
	@echo "\n\033[1m=== Running Smoke Tests ===\033[0m"
	PYTHONPATH=. $(PYTHON) -m pytest tests/smoke/ $(PYTEST_OPTS) || (echo "\033[1;31m❌ Smoke tests failed\033[0m"; exit 1)

## Run Playwright frontend tests
.PHONY: test-frontend
test-frontend: check-npm check-playwright
	@echo "\n\033[1m=== Running Playwright Frontend Tests ===\033[0m"
	@if ! pgrep -f "flask run" > /dev/null; then \
		echo "\033[1;33m⚠️  Flask app not running. Starting in background...\033[0m"; \
		$(PYTHON) -m flask run --host=127.0.0.1 --port=5000 > /dev/null 2>&1 & \
		FLASK_PID=$$!; \
		sleep 3; \
		npx playwright test tests/playwright/ || (echo "\033[1;31m❌ Frontend tests failed\033[0m"; kill $$FLASK_PID 2>/dev/null; exit 1); \
		kill $$FLASK_PID 2>/dev/null; \
	else \
		echo "\033[1;32m✅ Flask app is running\033[0m"; \
		npx playwright test tests/playwright/ || (echo "\033[1;31m❌ Frontend tests failed\033[0m"; exit 1); \
	fi
	@echo "\033[1;32m✅ Frontend tests completed\033[0m"

## Run security headers tests (both Playwright and Python)
.PHONY: test-security
test-security: check-npm check-playwright
	@echo "\n\033[1m=== Running Security Headers Tests ===\033[0m"
	@echo "\033[1m🔒 Testing Python integration tests...\033[0m"
	PYTHONPATH=. $(PYTHON) -m pytest tests/integration/test_security_headers.py $(PYTEST_OPTS) || (echo "\033[1;31m❌ Security integration tests failed\033[0m"; exit 1)
	@echo "\033[1m🎭 Testing Playwright security headers...\033[0m"
	@if ! pgrep -f "flask run" > /dev/null; then \
		echo "\033[1;33m⚠️  Flask app not running. Starting in background...\033[0m"; \
		$(PYTHON) -m flask run --host=127.0.0.1 --port=5000 > /dev/null 2>&1 & \
		FLASK_PID=$$!; \
		sleep 3; \
		npx playwright test tests/playwright/security-headers.spec.js || (echo "\033[1;31m❌ Security Playwright tests failed\033[0m"; kill $$FLASK_PID 2>/dev/null; exit 1); \
		kill $$FLASK_PID 2>/dev/null; \
	else \
		echo "\033[1;32m✅ Flask app is running\033[0m"; \
		npx playwright test tests/playwright/security-headers.spec.js || (echo "\033[1;31m❌ Security Playwright tests failed\033[0m"; exit 1); \
	fi
	@echo "\033[1;32m✅ Security headers tests completed\033[0m"

## Run console error tests
.PHONY: test-console
test-console: check-npm check-playwright
	@echo "\n\033[1m=== Running Console Error Tests ===\033[0m"
	@if ! pgrep -f "flask run" > /dev/null; then \
		echo "\033[1;33m⚠️  Flask app not running. Starting in background...\033[0m"; \
		$(PYTHON) -m flask run --host=127.0.0.1 --port=5000 > /dev/null 2>&1 & \
		FLASK_PID=$$!; \
		sleep 3; \
		npx playwright test tests/playwright/console-tests.spec.js || (echo "\033[1;31m❌ Console tests failed\033[0m"; kill $$FLASK_PID 2>/dev/null; exit 1); \
		kill $$FLASK_PID 2>/dev/null; \
	else \
		echo "\033[1;32m✅ Flask app is running\033[0m"; \
		npx playwright test tests/playwright/console-tests.spec.js || (echo "\033[1;31m❌ Console tests failed\033[0m"; exit 1); \
	fi
	@echo "\033[1;32m✅ Console error tests completed\033[0m"

## Run user flow tests (Playwright)
.PHONY: test-user-flows
test-user-flows: check-npm check-playwright setup-test-user
	@echo "\n\033[1m=== Running User Flow Tests ===\033[0m"
	@if ! pgrep -f "flask run" > /dev/null; then \
		echo "\033[1;33m⚠️  Flask app not running. Starting in background...\033[0m"; \
		$(PYTHON) -m flask run --host=127.0.0.1 --port=5000 > /dev/null 2>&1 & \
		FLASK_PID=$$!; \
		sleep 3; \
		BASE_URL=http://127.0.0.1:5000 npx playwright test tests/playwright/user-flows.spec.js || (echo "\033[1;31m❌ User flow tests failed\033[0m"; kill $$FLASK_PID 2>/dev/null; exit 1); \
		kill $$FLASK_PID 2>/dev/null; \
	else \
		echo "\033[1;32m✅ Flask app is running\033[0m"; \
		BASE_URL=http://127.0.0.1:5000 npx playwright test tests/playwright/user-flows.spec.js || (echo "\033[1;31m❌ User flow tests failed\033[0m"; exit 1); \
	fi
	@echo "\033[1;32m✅ User flow tests completed\033[0m"

## Run user flow tests in headed mode (see browser)
.PHONY: test-user-flows-headed
test-user-flows-headed: check-npm check-playwright setup-test-user
	@echo "\n\033[1m=== Running User Flow Tests (Headed Mode) ===\033[0m"
	@if ! pgrep -f "flask run" > /dev/null; then \
		echo "\033[1;33m⚠️  Flask app not running. Starting in background...\033[0m"; \
		$(PYTHON) -m flask run --host=127.0.0.1 --port=5000 > /dev/null 2>&1 & \
		FLASK_PID=$$!; \
		sleep 3; \
		BASE_URL=http://127.0.0.1:5000 npx playwright test tests/playwright/user-flows.spec.js --headed || (echo "\033[1;31m❌ User flow tests failed\033[0m"; kill $$FLASK_PID 2>/dev/null; exit 1); \
		kill $$FLASK_PID 2>/dev/null; \
	else \
		echo "\033[1;32m✅ Flask app is running\033[0m"; \
		BASE_URL=http://127.0.0.1:5000 npx playwright test tests/playwright/user-flows.spec.js --headed || (echo "\033[1;31m❌ User flow tests failed\033[0m"; exit 1); \
	fi
	@echo "\033[1;32m✅ User flow tests completed\033[0m"

## Run all frontend tests (Playwright)
.PHONY: test-e2e
test-e2e: test-frontend test-security test-console
	@echo "\n\033[1;32m✅ All end-to-end tests completed\033[0m"

## Install Playwright dependencies
.PHONY: install-playwright
install-playwright: check-npm
	@echo "\n\033[1m=== Installing Playwright ===\033[0m"
	@npm install @playwright/test
	@npx playwright install
	@echo "\033[1;32m✅ Playwright installed successfully\033[0m"

## Run Playwright tests in headed mode (see browser)
.PHONY: test-frontend-headed
test-frontend-headed: check-npm check-playwright
	@echo "\n\033[1m=== Running Playwright Tests (Headed Mode) ===\033[0m"
	@if ! pgrep -f "flask run" > /dev/null; then \
		echo "\033[1;33m⚠️  Flask app not running. Starting in background...\033[0m"; \
		$(PYTHON) -m flask run --host=127.0.0.1 --port=5000 > /dev/null 2>&1 & \
		FLASK_PID=$$!; \
		sleep 3; \
		npx playwright test tests/playwright/ --headed || (echo "\033[1;31m❌ Frontend tests failed\033[0m"; kill $$FLASK_PID 2>/dev/null; exit 1); \
		kill $$FLASK_PID 2>/dev/null; \
	else \
		echo "\033[1;32m✅ Flask app is running\033[0m"; \
		npx playwright test tests/playwright/ --headed || (echo "\033[1;31m❌ Frontend tests failed\033[0m"; exit 1); \
	fi

## Run Playwright tests in debug mode
.PHONY: test-frontend-debug
test-frontend-debug: check-npm check-playwright
	@echo "\n\033[1m=== Running Playwright Tests (Debug Mode) ===\033[0m"
	@if ! pgrep -f "flask run" > /dev/null; then \
		echo "\033[1;33m⚠️  Flask app not running. Starting in background...\033[0m"; \
		$(PYTHON) -m flask run --host=127.0.0.1 --port=5000 > /dev/null 2>&1 & \
		FLASK_PID=$$!; \
		sleep 3; \
		npx playwright test tests/playwright/ --debug || (echo "\033[1;31m❌ Frontend tests failed\033[0m"; kill $$FLASK_PID 2>/dev/null; exit 1); \
		kill $$FLASK_PID 2>/dev/null; \
	else \
		echo "\033[1;32m✅ Flask app is running\033[0m"; \
		npx playwright test tests/playwright/ --debug || (echo "\033[1;31m❌ Frontend tests failed\033[0m"; exit 1); \
	fi

## Generate Playwright test report
.PHONY: test-report
test-report: check-npm check-playwright
	@echo "\n\033[1m=== Generating Playwright Test Report ===\033[0m"
	@if ! pgrep -f "flask run" > /dev/null; then \
		echo "\033[1;33m⚠️  Flask app not running. Starting in background...\033[0m"; \
		$(PYTHON) -m flask run --host=127.0.0.1 --port=5000 > /dev/null 2>&1 & \
		FLASK_PID=$$!; \
		sleep 3; \
		npx playwright test tests/playwright/ --reporter=html || (echo "\033[1;31m❌ Frontend tests failed\033[0m"; kill $$FLASK_PID 2>/dev/null; exit 1); \
		kill $$FLASK_PID 2>/dev/null; \
	else \
		echo "\033[1;32m✅ Flask app is running\033[0m"; \
		npx playwright test tests/playwright/ --reporter=html || (echo "\033[1;31m❌ Frontend tests failed\033[0m"; exit 1); \
	fi
	@echo "\033[1;32m✅ Test report generated at playwright-report/index.html\033[0m"

# =============================================================================
# Database
# =============================================================================

## Initialize database
.PHONY: db-init
db-init: check-env
	$(PYTHON) init_db.py

## Run database migrations
.PHONY: db-migrate
db-migrate: check-env
	$(PYTHON) -m flask db migrate -m "$(shell date +%Y%m%d_%H%M%S)"

## Upgrade database
.PHONY: db-upgrade
db-upgrade: check-env
	$(PYTHON) -m flask db upgrade

## Downgrade database
.PHONY: db-downgrade
db-downgrade: check-env
	$(PYTHON) -m flask db downgrade

## Setup test user for Playwright tests
.PHONY: setup-test-user
setup-test-user: check-env
	@echo "\n\033[1m=== Setting up Test User ===\033[0m"
	@$(PYTHON) scripts/setup_test_user.py || (echo "\033[1;31m❌ Failed to setup test user\033[0m"; exit 1)
	@echo "\033[1;32m✅ Test user setup complete\033[0m"

# =============================================================================
# Docker
# =============================================================================

## Build for specific target (development, production, lambda)
.PHONY: docker-build
docker-build: validate-env
	@echo "\033[1m🔨 Building Docker image for $(TARGET) target...\033[0m"
	@TARGET_VAL=$(if $(TARGET),$(TARGET),development); \
	TAG_VAL=$(if $(TAG),$(TAG),latest); \
	docker buildx build \
		--platform $(TARGET_PLATFORM) \
		--target $$TARGET_VAL \
		-t $(IMAGE_NAME):$$TAG_VAL \
		--load \
		. || (echo "\033[1;31m❌ Docker build failed\033[0m"; exit 1)

## Fast development build (production deps only)
.PHONY: docker-build-fast
docker-build-fast: validate-env
	@echo "\033[1m⚡ Fast building Docker image for development...\033[0m"
	@docker build \
		-f Dockerfile.dev-fast \
		-t $(IMAGE_NAME):dev-fast \
		--load \
		. || (echo "\033[1;31m❌ Fast Docker build failed\033[0m"; exit 1)

## Standard build (now optimized by default)
.PHONY: docker-build-standard
docker-build-standard: validate-env
	@echo "\033[1m🚀 Building standard Docker image (optimized)...\033[0m"
	@TARGET_VAL=$(if $(TARGET),$(TARGET),development); \
	TAG_VAL=$(if $(TAG),$(TAG),standard); \
	docker buildx build \
		--platform $(TARGET_PLATFORM) \
		--target $$TARGET_VAL \
		-t $(IMAGE_NAME):$$TAG_VAL \
		--load \
		. || (echo "\033[1;31m❌ Standard Docker build failed\033[0m"; exit 1)
	@echo "\033[1;32m✅ Docker image built successfully\033[0m"

## Quick development build
.PHONY: docker-dev
docker-dev: TARGET := development
docker-dev: TAG := dev
docker-dev: docker-build

## Quick production build
.PHONY: docker-prod
docker-prod: TARGET := production
docker-prod: TAG := prod
docker-prod: docker-build

## Start development environment
.PHONY: docker-up
docker-up:
	@echo "\033[1m🚀 Starting development environment...\033[0m"
	$(DOCKER_COMPOSE) up -d
	@echo "\033[1;32m✅ Development environment started\033[0m"
	@echo "\033[1;36m📱 Web app: http://localhost:8000\033[0m"
	@echo "\033[1;36m🗄️  Database: localhost:5432\033[0m"
	@echo "\033[1;36m🔧 Adminer: http://localhost:8081\033[0m"

## Stop development environment
.PHONY: docker-down
docker-down:
	@echo "\033[1m🛑 Stopping development environment...\033[0m"
	$(DOCKER_COMPOSE) down
	@echo "\033[1;32m✅ Development environment stopped\033[0m"

## View logs
.PHONY: docker-logs
docker-logs:
	$(DOCKER_COMPOSE) logs -f

## Open shell in container
.PHONY: docker-shell
docker-shell:
	docker exec -it $(CONTAINER_NAME) /bin/bash

## Clean up Docker resources
.PHONY: docker-clean
docker-clean: docker-down
	@echo "\033[1m🧹 Cleaning up Docker resources...\033[0m"
	@docker system prune -f
	@docker volume prune -f
	@echo "\033[1;32m✅ Docker cleanup completed\033[0m"

## Rebuild and restart (development)
.PHONY: docker-rebuild
docker-rebuild: docker-down docker-dev docker-up
	@echo "\033[1;32m✅ Rebuild and restart completed\033[0m"

# =============================================================================
# Terraform
# =============================================================================

## Initialize Terraform for a specific environment
.PHONY: tf-init
tf-init: validate-tf-config
	@echo "🚀 Initializing Terraform in $(TF_ENV) environment..."
	@cd terraform && \
	TF_PLUGIN_CACHE_DIR="$(HOME)/.terraform.d/plugin-cache" \
	TF_IN_AUTOMATION=1 \
	terraform init -reconfigure -backend-config=environments/$(TF_ENV)/backend.hcl

## Generate a plan without applying
.PHONY: tf-plan
tf-plan: validate-tf-config
	@echo "Creating Terraform plan for environment: $(TF_ENV)"
	@cd terraform && \
	terraform plan \
		-var-file=environments/$(TF_ENV)/terraform.tfvars \
		-out=environments/$(TF_ENV)/tfplan-$(TF_ENV) \
		-var="environment=$(TF_ENV)" \
		-input=false \
		-lock=true \
		-parallelism=$(TF_PARALLELISM)

## Apply the most recent plan
.PHONY: tf-apply
tf-apply: validate-tf-config
	@if [ ! -f "terraform/environments/$(TF_ENV)/tfplan-$(TF_ENV)" ]; then \
		echo "\033[1;31m❌ No Terraform plan found. Run 'make tf-plan' first.\033[0m"; \
		exit 1; \
	fi
	@echo "\033[1m🚀 Applying Terraform changes to environment: $(TF_ENV)\033[0m"
	@read -p "Are you sure you want to apply these changes? [y/N] " confirm && \
		[ $$confirm = y ] || [ $$confirm = Y ] || (echo "\033[1;33m⚠️  Aborting...\033[0m"; exit 1)
	@cd terraform && \
	terraform apply \
		-input=false \
		-lock=true \
		-parallelism=$(TF_PARALLELISM) \
		environments/$(TF_ENV)/tfplan-$(TF_ENV) || (echo "\033[1;31m❌ Terraform apply failed\033[0m"; exit 1)
	@echo "\033[1;32m✅ Terraform changes applied successfully\033[0m"

## Destroy all resources in the environment
.PHONY: tf-destroy
tf-destroy: validate-tf-config
	@echo "\033[1;31m⚠️  WARNING: This will destroy all resources in the $(TF_ENV) environment!\033[0m"
	@echo "\033[1;31m⚠️  This action cannot be undone!\033[0m"
	@read -p "Type 'DESTROY $(TF_ENV)' to continue: " confirm && \
		[ "$$confirm" = "DESTROY $(TF_ENV)" ] || (echo "\033[1;33m⚠️  Aborting...\033[0m"; exit 1)
	@echo "\033[1m🗑️  Destroying all resources in environment: $(TF_ENV)\033[0m"
	@cd terraform && \
	terraform destroy \
		-var-file=environments/$(TF_ENV)/terraform.tfvars \
		-var="environment=$(TF_ENV)" \
		-input=false \
		-lock=true \
		-parallelism=$(TF_PARALLELISM) \
		-auto-approve || (echo "\033[1;31m❌ Terraform destroy failed\033[0m"; exit 1)
	@echo "\033[1;32m✅ All resources destroyed successfully\033[0m"

## Validate Terraform configuration
.PHONY: tf-validate
tf-validate:
	@echo "Validating Terraform configuration for $(TF_ENV)..."
	@cd terraform && \
	terraform validate

## Validate Terraform configuration and environment
.PHONY: validate-tf-config
validate-tf-config:
	@echo "\033[1m🔍 Validating Terraform configuration...\033[0m"
	@if [ -z "$(TF_ENV)" ]; then \
		echo "\033[1;31m❌ TF_ENV is not set\033[0m"; \
		exit 1; \
	fi
	@if [ ! -d "terraform/environments/$(TF_ENV)" ]; then \
		echo "\033[1;31m❌ Terraform environment '$(TF_ENV)' not found\033[0m"; \
		exit 1; \
	fi
	@if [ ! -f "terraform/environments/$(TF_ENV)/terraform.tfvars" ]; then \
		echo "\033[1;31m❌ terraform.tfvars not found in terraform/environments/$(TF_ENV)/\033[0m"; \
		exit 1; \
	fi
	@echo "\033[1;32m✅ Terraform configuration validated\033[0m"

# =============================================================================
# Deployment
# =============================================================================

## Deploy to dev environment
.PHONY: deploy-dev
deploy-dev: validate-env check-lambda-package
	@echo "\033[1m🚀 Deploying to dev environment...\033[0m"
	@./scripts/deploy_lambda.sh \
	  --function "$(LAMBDA_FUNCTION_NAME)-dev" \
	  --env dev \
	  --no-package || (echo "\033[1;31m❌ Dev deployment failed\033[0m"; exit 1)
	@echo "\033[1;32m✅ Dev deployment completed successfully\033[0m"

## Deploy to staging environment
.PHONY: deploy-staging
deploy-staging: validate-env check-lambda-package
	@echo "\033[1m🚀 Deploying to staging environment...\033[0m"
	@read -p "This will deploy to the staging environment. Continue? [y/N] " confirm && [ "$$confirm" = "y" ] || [ "$$confirm" = "Y" ] || (echo "\033[1;33m⚠️  Aborting...\033[0m"; exit 1)
	@./scripts/deploy_lambda.sh \
	  --function "$(LAMBDA_FUNCTION_NAME)-staging" \
	  --env staging \
	  --no-package || (echo "\033[1;31m❌ Staging deployment failed\033[0m"; exit 1)
	@echo "\033[1;32m✅ Staging deployment completed successfully\033[0m"

## Deploy to production environment
.PHONY: deploy-prod
deploy-prod: validate-env check-lambda-package
	@echo "\033[1;31m⚠️  WARNING: You are about to deploy to PRODUCTION!\033[0m"
	@echo "\033[1;31m⚠️  This will apply all pending changes to your production environment.\033[0m"
	@read -p "Type 'production' to continue: " confirm && [ "$$confirm" = "production" ]
	@./scripts/deploy_lambda.sh \
	  --function "$(LAMBDA_FUNCTION_NAME)" \
	  --env prod \
	  --no-package || (echo "\033[1;31m❌ Production deployment failed\033[0m"; exit 1)
	@echo "\033[1;32m✅ Production deployment completed successfully\033[0m"

## Release to staging environment (tag-based)
.PHONY: release-staging
release-staging: validate-env
	@echo "\033[1m🚀 Releasing to staging environment...\033[0m"
	@if [ -z "$(TAG)" ]; then \
		echo "\033[1;31m❌ TAG is required for release. Usage: make release-staging TAG=v1.0.0\033[0m"; \
		exit 1; \
	fi
	@echo "\033[1;33m⚠️  This will trigger a release workflow for tag $(TAG)\033[0m"
	@read -p "Continue with staging release? [y/N] " confirm && [ "$$confirm" = "y" ] || [ "$$confirm" = "Y" ] || (echo "\033[1;33m⚠️  Aborting...\033[0m"; exit 1)
	@gh workflow run release.yml --ref $(TAG) --field environment=staging --field tag=$(TAG)
	@echo "\033[1;32m✅ Staging release workflow triggered for tag $(TAG)\033[0m"

## Release to production environment (tag-based)
.PHONY: release-prod
release-prod: validate-env
	@echo "\033[1;31m⚠️  WARNING: You are about to release to PRODUCTION!\033[0m"
	@echo "\033[1;31m⚠️  This will trigger a production release workflow.\033[0m"
	@if [ -z "$(TAG)" ]; then \
		echo "\033[1;31m❌ TAG is required for release. Usage: make release-prod TAG=v1.0.0\033[0m"; \
		exit 1; \
	fi
	@read -p "Type 'production' to continue: " confirm && [ "$$confirm" = "production" ]
	@gh workflow run release.yml --ref $(TAG) --field environment=prod --field tag=$(TAG)
	@echo "\033[1;32m✅ Production release workflow triggered for tag $(TAG)\033[0m"

## Check Lambda package exists
.PHONY: check-lambda-package
check-lambda-package:
	@ARCHITECTURE="$${LAMBDA_ARCHITECTURE:-arm64}"; \
	if [ ! -f "dist/$$ARCHITECTURE/app/app-$$ARCHITECTURE.zip" ]; then \
		echo "\033[1;33m⚠️  Lambda package (dist/$$ARCHITECTURE/app/app-$$ARCHITECTURE.zip) not found.\033[0m"; \
		echo -n "Run 'make package' to create it now? [y/N] "; \
		read -r -n 1; \
		if [[ "$$REPLY" =~ ^[Yy]$$ ]]; then \
			echo ""; \
			$(MAKE) package; \
			if [ ! -f "dist/$$ARCHITECTURE/app/app-$$ARCHITECTURE.zip" ]; then \
				echo "\033[1;31m❌ Package creation failed. Please fix the issues and try again.\033[0m"; \
				exit 1; \
			fi; \
		else \
			echo "\n\033[1;31m❌ Aborting: Lambda package is required for deployment.\033[0m"; \
			exit 1; \
		fi; \
	fi

## Package Lambda deployment (architecture-aware)
.PHONY: package
package:
	@echo "\033[1m⚡ Creating Lambda deployment package...\033[0m"
	@if [ ! -x "$(shell which zip)" ]; then \
		echo "Error: 'zip' command is required but not installed."; \
		exit 1; \
	fi
	@chmod +x scripts/package.sh
	@if ! ./scripts/package.sh; then \
		echo "\033[1;31m❌ Failed to create Lambda package\033[0m"; \
		exit 1; \
	fi
	@echo "\033[1;32m✅ Lambda package created\033[0m"

## Package Lambda deployment (alias for package)
.PHONY: package-lambda
package-lambda: package

## Lambda layer package (architecture-aware with Docker fallback)
.PHONY: package-layer
package-layer:
	@echo "\033[1m⚡ Creating Lambda layer package...\033[0m"
	@if [ ! -x "$(shell which zip)" ]; then \
		echo "Error: 'zip' command is required but not installed."; \
		exit 1; \
	fi
	@chmod +x scripts/package.sh
	@if ! ./scripts/package.sh -l; then \
		echo "\033[1;31m❌ Failed to create Lambda layer package\033[0m"; \
		exit 1; \
	fi
	@echo "\033[1;32m✅ Lambda layer package created\033[0m"

## Complete Lambda package (app + layer, architecture-aware)
.PHONY: package-complete
package-complete:
	@echo "\033[1m⚡ Creating complete Lambda package (app + layer)...\033[0m"
	@if [ ! -x "$(shell which zip)" ]; then \
		echo "Error: 'zip' command is required but not installed."; \
		exit 1; \
	fi
	@chmod +x scripts/package.sh
	@if ! ./scripts/package.sh -b; then \
		echo "\033[1;31m❌ Failed to create complete Lambda package\033[0m"; \
		exit 1; \
	fi
	@echo "\033[1;32m✅ Complete Lambda package created\033[0m"

## Layer package for x86_64 (current platform)
.PHONY: package-layer-x86
package-layer-x86:
	@echo "\033[1m⚡ Creating x86_64 Lambda layer package...\033[0m"
	@if [ ! -x "$(shell which zip)" ]; then \
		echo "Error: 'zip' command is required but not installed."; \
		exit 1; \
	fi
	@chmod +x scripts/package.sh
	@if ! ./scripts/package.sh -l --x86_64; then \
		echo "\033[1;31m❌ Failed to create x86_64 layer package\033[0m"; \
		exit 1; \
	fi
	@echo "\033[1;32m✅ x86_64 layer package created\033[0m"

## Layer package for ARM64 (with Docker fallback for cross-architecture)
.PHONY: package-layer-arm
package-layer-arm:
	@echo "\033[1m⚡ Creating ARM64 Lambda layer package...\033[0m"
	@if [ ! -x "$(shell which zip)" ]; then \
		echo "Error: 'zip' command is required but not installed."; \
		exit 1; \
	fi
	@chmod +x scripts/package.sh
	@if ! ./scripts/package.sh -l --arm64; then \
		echo "\033[1;31m❌ Failed to create ARM64 layer package\033[0m"; \
		exit 1; \
	fi
	@echo "\033[1;32m✅ ARM64 layer package created\033[0m"

# =============================================================================
# Utilities
# =============================================================================

## Clean up build artifacts and temporary files
.PHONY: clean
clean: docker-clean
	find . -type d -name "__pycache__" -exec rm -r {} + 2>/dev/null || true
	find . -type f -name "*.py[co]" -delete 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -r {} + 2>/dev/null || true
	rm -rf .coverage htmlcov/ tmp/ dist/ 2>/dev/null || true

## Remove all generated files including virtual environment
.PHONY: distclean
distclean: clean
	rm -rf venv/ .venv/ .env.local 2>/dev/null || true

## Check development environment setup
.PHONY: check-env
check-env:
	@echo "\033[1m🔍 Checking development environment...\033[0m"
	@if [ ! -d "venv" ]; then \
		echo "\033[1;31m❌ Virtual environment not found. Run 'make venv' first.\033[0m"; \
		exit 1; \
	fi

## Check npm dependencies
.PHONY: check-npm
check-npm:
	@echo "\033[1m🔍 Checking npm dependencies...\033[0m"
	@if [ ! -d "node_modules" ]; then \
		echo "\033[1;33m⚠️  npm dependencies not found. Installing...\033[0m"; \
		npm install; \
	fi

## Check Playwright installation
.PHONY: check-playwright
check-playwright: check-npm
	@echo "\033[1m🔍 Checking Playwright installation...\033[0m"
	@if ! command -v npx >/dev/null 2>&1; then \
		echo "\033[1;31m❌ npx not found. Please install Node.js and npm.\033[0m"; \
		exit 1; \
	fi
	@if ! npx playwright --version >/dev/null 2>&1; then \
		echo "\033[1;33m⚠️  Playwright not found. Installing...\033[0m"; \
		npm install @playwright/test; \
		npx playwright install; \
	fi
	@echo "\033[1;32m✅ Playwright is available\033[0m"

## Validate all required tools and environment
.PHONY: validate-env
validate-env: check-env
	@echo "\033[1m🔍 Validating development environment...\033[0m"
	@command -v docker >/dev/null 2>&1 || (echo "\033[1;31m❌ Docker not found\033[0m"; exit 1)
	@command -v terraform >/dev/null 2>&1 || (echo "\033[1;31m❌ Terraform not found\033[0m"; exit 1)
	@command -v aws >/dev/null 2>&1 || (echo "\033[1;33m⚠️  AWS CLI not found\033[0m")
	@echo "\033[1;32m✅ Environment validation completed\033[0m"

# =============================================================================
# Aliases for backward compatibility
# =============================================================================
.PHONY: build stop logs restart run-local rebuild-logs
build: docker-build
stop: docker-down
logs: docker-logs
restart: docker-down docker-up
run-local: run
rebuild-logs: docker-rebuild docker-logs
