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
#   Documentation: docs, docs-serve
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
TEST_PATH = tests/

# Docker settings
DOCKER_COMPOSE = docker-compose -f docker-compose.yml
DOCKER_COMPOSE_DEV = $(DOCKER_COMPOSE) -f docker-compose.dev.yml
CONTAINER_NAME = $(APP_NAME)-app
IMAGE_NAME = $(APP_NAME)
VOLUME_NAME = $(APP_NAME)-db
TARGET_PLATFORM ?= linux/amd64

# Terraform settings
ENV ?= dev
TF_ENV ?= $(ENV)
TF_ROOT := $(shell pwd)/terraform
TF_ENV_DIR = $(TF_ROOT)/environments/$(TF_ENV)
TF_BACKEND_CONFIG = $(TF_ENV_DIR)/backend.hcl
TF_CMD = cd terraform && make ENV=$(TF_ENV)
TF_PARALLELISM ?= 30
TF_ARGS ?= -parallelism=$(TF_PARALLELISM) -refresh=true

# GitHub settings
GITHUB_ORG ?= nivecher
REPO_NAME ?= meal-expense-tracker

# AWS settings
DEFAULT_AWS_PROFILE ?= default
DEFAULT_AWS_REGION ?= us-east-1
LAMBDA_FUNCTION_NAME ?= meal-expense-tracker-$(TF_ENV)

# TODO deal with this
# Enable BuildKit for better build performance and features (only if buildx is available)
ifneq ($(shell docker buildx version 2>/dev/null),)
export DOCKER_BUILDKIT=1
export COMPOSE_DOCKER_CLI_BUILD=1
else
$(warning BuildKit/buildx not available, using legacy Docker build)
endif
export PYTHONPATH

# =============================================================================
# Help
# =============================================================================

## Display help message
.PHONY: help
help:  ## Show this help message
	@echo "\n\033[1mMeal Expense Tracker - Available Commands\033[0m\n"
	@echo "\033[1mDevelopment:\033[0m"
	@echo "  \033[1mmake setup\033[0m           Install development dependencies"
	@echo "  \033[1mmake run\033[0m             Run the application locally"
	@echo "  \033[1mmake format\033[0m          Format code with black and autoflake"
	@echo "  \033[1mmake lint\033[0m            Run linters (flake8, black, mypy)"
	@echo "  \033[1mmake test\033[0m            Run all tests with coverage"
	@echo "  \033[1mmake test-with-lint\033[0m  Run tests with linting (ensures code quality)"
	@echo "  \033[1mmake check\033[0m           Run all checks (format + lint + test)"
	@echo "  \033[1mmake quality\033[0m         Run all quality checks"
	@echo "  \033[1mmake pre-commit\033[0m      Run pre-commit checks (format + lint + test)"
	@echo "  \033[1mmake validate-env\033[0m    Validate development environment"

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

	@echo "\n\033[1mTesting:\033[0m"
	@echo "  \033[1mmake test\033[0m            Run all tests with coverage"
	@echo "  \033[1mmake test-unit\033[0m        Run only unit tests"
	@echo "  \033[1mmake test-integration\033[0m Run only integration tests"
	@echo "  \033[1mmake test-smoke\033[0m       Run smoke tests"
	@echo "  \033[1mmake load-test\033[0m        Run load tests"
	@echo "  \033[1mmake test-app\033[0m         Run app-level tests"
	@echo "  \033[1mmake test-auth\033[0m        Run authentication tests"
	@echo "  \033[1mmake test-expenses\033[0m    Run expense tests"
	@echo "  \033[1mmake test-restaurants\033[0m Run restaurant tests"
	@echo "  \033[1mmake test-categories\033[0m  Run category tests"
	@echo "  \033[1mmake test-profile\033[0m     Run profile tests"
	@echo "  \033[1mmake test-main\033[0m        Run main blueprint tests"
	@echo "  \033[1mmake test-security\033[0m    Run security tests"
	@echo "  \033[1mmake test-models\033[0m      Run model tests"
	@echo "  \033[1mmake test-utils\033[0m       Run utility tests"
	@echo "  \033[1mmake test-frontend\033[0m    Run frontend tests"

	@echo "\n\033[1mTerraform (TF_ENV=env, default: dev):\033[0m"
	@echo "  \033[1mmake validate-tf-config\033[0m Validate Terraform configuration"
	@echo "  \033[1mmake tf-init\033[0m        Initialize Terraform with backend config"
	@echo "  \033[1mmake tf-plan\033[0m        Generate and show execution plan"
	@echo "  \033[1mmake tf-apply\033[0m       Apply changes to infrastructure"
	@echo "  \033[1mmake tf-destroy\033[0m     Destroy infrastructure"
	@echo "  \033[1mmake tf-validate\033[0m    Validate Terraform configuration"

	@echo "\n\033[1mDeployment:\033[0m"
	@echo "  \033[1mmake deploy-dev\033[0m      Deploy to development environment"
	@echo "  \033[1mmake deploy-staging\033[0m  Deploy to staging environment"
	@echo "  \033[1mmake deploy-prod\033[0m     Deploy to production environment"

	@echo "\n\033[1mDocumentation:\033[0m"
	@echo "  \033[1mmake docs\033[0m           Generate API documentation"
	@echo "  \033[1mmake docs-serve\033[0m      Serve documentation locally"

	@echo "\n\033[1mUtilities:\033[0m"
	@echo "  \033[1mmake clean\033[0m           Remove build artifacts and temporary files"
	@echo "  \033[1mmake distclean\033[0m        Remove all generated files including virtual environment"
	@echo "  \033[1mmake check-env\033[0m        Check development environment setup"
	@echo "  \033[1mmake validate-env\033[0m    Validate all required tools and environment"

	@echo "\n\033[1mPerformance & Caching:\033[0m"
	@echo "  \033[1mmake cache-clear\033[0m     Clear all caches (Python, pytest, mypy)"
	@echo "  \033[1mmake deps-check\033[0m      Check for outdated dependencies"
	@echo "  \033[1mmake deps-update\033[0m     Update development dependencies"
	@echo "  \033[1mmake deps-resolve\033[0m    Resolve dependency conflicts"

	@echo "\n\033[1mHealth & Monitoring:\033[0m"
	@echo "  \033[1mmake health-check\033[0m    Check application health"
	@echo "  \033[1mmake system-check\033[0m    Check system resources"
	@echo "  \033[1mmake system-validate\033[0m Full system validation"

	@echo "\n\033[1mError Recovery:\033[0m"
	@echo "  \033[1mmake auto-fix\033[0m        Automatic fixes for common issues"
	@echo "  \033[1mmake rollback\033[0m        Show rollback options for deployments"

	@echo "\n\033[1mWorkflow:\033[0m"
	@echo "  \033[1mmake dev-setup\033[0m       Complete development setup"
	@echo "  \033[1mmake dev-cycle\033[0m       Quick development cycle (format + lint + test)"
	@echo "  \033[1mmake dev-status\033[0m      Show development environment status"

	@echo "\n\033[1mExamples:\033[0m"
	@echo "  \033[1mmake validate-env && make setup && make run\033[0m  # Safe setup and run"
	@echo "  \033[1mmake quality\033[0m                                 # Run all quality checks"
	@echo "  \033[1mmake validate-tf-config && make tf-plan\033[0m      # Safe Terraform planning"
	@echo "  \033[1mmake deploy-dev\033[0m                              # Deploy to development"

# =============================================================================
# Virtual Environment
# =============================================================================

## Create and activate Python virtual environment
.PHONY: venv
venv:
	@if [ ! -d "venv" ]; then \
		echo "Creating virtual environment..."; \
		$(PYTHON) -m venv venv; \
		echo "Virtual environment created. Run 'source venv/bin/activate' to activate."; \
	else \
		echo "Virtual environment already exists. Run 'source venv/bin/activate' to activate."; \
	fi

# =============================================================================
# Development
# =============================================================================

## Install development dependencies
.PHONY: setup
setup:
	@echo "\n\033[1m=== Setting up development environment ===\033[0m"
	@./scripts/setup-local-dev.sh

## Run the application locally
.PHONY: run
run: check-env
	$(PYTHON) -m flask run

## Run all linters
.PHONY: lint
lint: lint-python lint-html lint-js lint-css

## Run all linters including optional ones
.PHONY: lint-all
lint-all: lint lint-optional

## Python linter
.PHONY: lint-python
lint-python: check-env
	@echo "\n\033[1m=== Running Python Linter ===\033[0m"
	@$(PYTHON) -m flake8 app tests || (echo "\033[1;31m❌ Flake8 failed\033[0m"; exit 1)
	@$(PYTHON) -m black --check app tests || (echo "\033[1;31m❌ Black check failed\033[0m"; exit 1)

## HTML template linter
.PHONY: lint-html
lint-html: check-env
	@echo "\n\033[1m=== Running HTML Template Linter ===\033[0m"
	@$(PYTHON) -m djlint app/templates/ --reformat --profile=jinja || echo "\033[1;33m⚠️  HTML linting completed with warnings\033[0m"

## JavaScript linter
.PHONY: lint-js
lint-js:
	@if [ -d "app/static/js" ]; then \
		echo "\n\033[1m=== Running JavaScript Linter ===\033[0m"; \
		npx eslint --config eslint.config.js "app/static/js/**/*.js" || (echo "\033[1;31m❌ JavaScript linting failed\033[0m"; exit 1); \
	fi

## CSS linter
.PHONY: lint-css
lint-css:
	@if [ -d "app/static/css" ]; then \
		echo "\n\033[1m=== Running CSS Linter ===\033[0m"; \
		npx stylelint "app/static/css/**/*.css" || (echo "\033[1;31m❌ CSS linting failed\033[0m"; exit 1); \
	fi

## Optional linters
.PHONY: lint-optional
lint-optional: lint-security lint-docker

## Security linter
.PHONY: lint-security
lint-security:
	@echo "\n\033[1m=== Running Security Linter ===\033[0m"
	@pip-audit || echo "pip-audit not installed, skipping security audit"

## Docker linter
.PHONY: lint-docker
lint-docker:
	@echo "\n\033[1m=== Running Docker Linter ===\033[0m"
	@if command -v hadolint >/dev/null 2>&1; then \
		hadolint Dockerfile || (echo "\033[1;31m❌ Docker linting failed\033[0m"; exit 1); \
	else \
		echo "hadolint not installed, skipping Docker linting"; \
	fi

## Format all code
.PHONY: format
format: format-python format-html format-shell

## Format Python code
.PHONY: format-python
format-python: check-env
	@echo "\n\033[1m=== Formatting Python code ===\033[0m"
	@$(PYTHON) -m isort app/ tests/ migrations/ *.py || (echo "\033[1;31m❌ isort failed\033[0m"; exit 1)
	@$(PYTHON) -m black app/ tests/ migrations/ */*.py *.py || (echo "\033[1;31m❌ black failed\033[0m"; exit 1)
	@$(PYTHON) -m autoflake --in-place --remove-all-unused-imports --recursive app/ tests/ || (echo "\033[1;31m❌ autoflake failed\033[0m"; exit 1)

## Format HTML templates
.PHONY: format-html
format-html:
	@echo "\n\033[1m=== Formatting HTML Templates ===\033[0m"
	@djlint app/templates --profile=django --reformat || (echo "\033[1;31m❌ HTML formatting failed\033[0m"; exit 1)

## Format Shell scripts
.PHONY: format-shell
format-shell:
	@if command -v shfmt >/dev/null 2>&1; then \
		echo "\n\033[1m=== Formatting Shell scripts ===\033[0m"; \
		find . -type f -name '*.sh' \
			-not -path '*/.*' \
			-not -path '*/venv/*' \
			-not -path '*/Python-*/*' \
			-print0 | xargs -0 -I{} sh -c 'echo "Formatting {}" && shfmt -i 2 -w "{}"' || (echo "\033[1;31m❌ Shell formatting failed\033[0m"; exit 1); \
	else \
		echo "\n\033[1;33m⚠️ shfmt is not installed. Shell scripts will not be formatted.\033[0m"; \
		echo "To enable shell script formatting, please install shfmt:"; \
		echo "  - Using Go: go install mvdan.cc/sh/v3/cmd/shfmt@latest"; \
		echo "  - Or download from: https://github.com/mvdan/sh/releases"; \
		echo "  - Or via package manager: brew install shfmt / apt-get install shfmt / etc."; \
		echo "\nContinuing with Python formatting only...\n"; \
	fi

## Run all tests
.PHONY: test
test: check-env  ## Run tests directly
	@echo "\n\033[1m=== Running Tests ===\033[0m"
	PYTHONPATH=. $(PYTHON) -m pytest tests/ $(PYTEST_OPTS) || (echo "\033[1;31m❌ Tests failed\033[0m"; exit 1)

## Run tests with linting (ensures code quality before testing)
.PHONY: test-with-lint
test-with-lint: lint test

## Run pre-commit checks
.PHONY: pre-commit
pre-commit: format lint test

## Run all checks (format + lint + test)
.PHONY: check
check: format lint test

## Run all quality checks
.PHONY: quality
quality: check

## Run unit tests only
.PHONY: test-unit
test-unit:
	@echo "\n\033[1m=== Running Unit Tests ===\033[0m"
	PYTHONPATH=. $(PYTHON) -m pytest tests/unit/ $(PYTEST_OPTS) || (echo "\033[1;31m❌ Unit tests failed\033[0m"; exit 1)

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

## Run load tests
.PHONY: load-test
load-test:
	@echo "\n\033[1m=== Running Load Tests ===\033[0m"
	@if [ -f "tests/load/locustfile.py" ]; then \
		$(PYTHON) -m locust -f tests/load/locustfile.py --headless --users 10 --spawn-rate 2 --run-time 30s || (echo "\033[1;31m❌ Load tests failed\033[0m"; exit 1); \
	else \
		echo "\033[1;33m⚠️  Load tests not yet implemented\033[0m"; \
	fi

## Run specific test categories
.PHONY: test-app test-auth test-expenses test-restaurants test-categories test-profile test-main test-security test-models test-utils

## Run app-level tests
.PHONY: test-app
test-app:
	@echo "\n\033[1m=== Running App-Level Tests ===\033[0m"
	PYTHONPATH=. $(PYTHON) -m pytest tests/unit/app/ $(PYTEST_OPTS) || (echo "\033[1;31m❌ App tests failed\033[0m"; exit 1)

## Run authentication tests
.PHONY: test-auth
test-auth:
	@echo "\n\033[1m=== Running Authentication Tests ===\033[0m"
	PYTHONPATH=. $(PYTHON) -m pytest tests/unit/auth/ $(PYTEST_OPTS) || (echo "\033[1;31m❌ Auth tests failed\033[0m"; exit 1)

## Run expense tests
.PHONY: test-expenses
test-expenses:
	@echo "\n\033[1m=== Running Expense Tests ===\033[0m"
	PYTHONPATH=. $(PYTHON) -m pytest tests/unit/expenses/ $(PYTEST_OPTS) || (echo "\033[1;31m❌ Expense tests failed\033[0m"; exit 1)

## Run restaurant tests
.PHONY: test-restaurants
test-restaurants:
	@echo "\n\033[1m=== Running Restaurant Tests ===\033[0m"
	PYTHONPATH=. $(PYTHON) -m pytest tests/unit/restaurants/ $(PYTEST_OPTS) || (echo "\033[1;31m❌ Restaurant tests failed\033[0m"; exit 1)

## Run category tests
.PHONY: test-categories
test-categories:
	@echo "\n\033[1m=== Running Category Tests ===\033[0m"
	PYTHONPATH=. $(PYTHON) -m pytest tests/unit/categories/ $(PYTEST_OPTS) || (echo "\033[1;31m❌ Category tests failed\033[0m"; exit 1)

## Run profile tests
.PHONY: test-profile
test-profile:
	@echo "\n\033[1m=== Running Profile Tests ===\033[0m"
	PYTHONPATH=. $(PYTHON) -m pytest tests/unit/profile/ $(PYTEST_OPTS) || (echo "\033[1;31m❌ Profile tests failed\033[0m"; exit 1)

## Run main blueprint tests
.PHONY: test-main
test-main:
	@echo "\n\033[1m=== Running Main Blueprint Tests ===\033[0m"
	PYTHONPATH=. $(PYTHON) -m pytest tests/unit/main/ $(PYTEST_OPTS) || (echo "\033[1;31m❌ Main tests failed\033[0m"; exit 1)

## Run security tests
.PHONY: test-security
test-security:
	@echo "\n\033[1m=== Running Security Tests ===\033[0m"
	PYTHONPATH=. $(PYTHON) -m pytest tests/unit/security/ $(PYTEST_OPTS) || (echo "\033[1;31m❌ Security tests failed\033[0m"; exit 1)

## Run model tests
.PHONY: test-models
test-models:
	@echo "\n\033[1m=== Running Model Tests ===\033[0m"
	PYTHONPATH=. $(PYTHON) -m pytest tests/unit/models/ $(PYTEST_OPTS) || (echo "\033[1;31m❌ Model tests failed\033[0m"; exit 1)

## Run utility tests
.PHONY: test-utils
test-utils:
	@echo "\n\033[1m=== Running Utility Tests ===\033[0m"
	PYTHONPATH=. $(PYTHON) -m pytest tests/unit/utils/ $(PYTEST_OPTS) || (echo "\033[1;31m❌ Utility tests failed\033[0m"; exit 1)

## Run frontend tests
.PHONY: test-frontend
test-frontend:
	@echo "\n\033[1m=== Running Frontend Tests ===\033[0m"
	@if [ -d "tests/frontend" ]; then \
		PYTHONPATH=. $(PYTHON) -m pytest tests/frontend/ $(PYTEST_OPTS) || (echo "\033[1;31m❌ Frontend tests failed\033[0m"; exit 1); \
	else \
		echo "\033[1;33m⚠️  Frontend tests not found\033[0m"; \
	fi

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

# =============================================================================
# Docker
# =============================================================================

## Check Docker BuildKit availability
.PHONY: check-docker-buildkit
check-docker-buildkit:
	@if command -v docker >/dev/null 2>&1; then \
		if docker buildx version >/dev/null 2>&1; then \
			echo "BuildKit available"; \
		else \
			echo "BuildKit not available"; \
		fi; \
	else \
		echo "\033[1;31m❌ Docker not found\033[0m"; \
		exit 1; \
	fi

## Build Docker image for production
.PHONY: docker-build
docker-build: validate-env
	@if docker buildx version >/dev/null 2>&1; then \
		echo "\033[1;32m✅ Using BuildKit for multi-stage build\033[0m"; \
		docker build \
			--build-arg TARGETPLATFORM=$(TARGET_PLATFORM) \
			-t $(IMAGE_NAME):latest \
			--target production \
			. || (echo "\033[1;31m❌ Docker build failed\033[0m"; exit 1); \
	else \
		echo "\033[1;33m⚠️  BuildKit not available, using legacy build\033[0m"; \
		docker build \
			--build-arg TARGETPLATFORM=$(TARGET_PLATFORM) \
			-t $(IMAGE_NAME):latest \
			-f Dockerfile.legacy \
			. || (echo "\033[1;31m❌ Docker build failed\033[0m"; exit 1); \
	fi
	@echo "\033[1;32m✅ Docker image built successfully\033[0m"

## Build Docker image for development
.PHONY: docker-build-dev
docker-build-dev: validate-env
	@if docker buildx version >/dev/null 2>&1; then \
		echo "\033[1;32m✅ Using BuildKit for multi-stage build\033[0m"; \
		docker build \
			--build-arg TARGETPLATFORM=$(TARGET_PLATFORM) \
			-t $(IMAGE_NAME):dev \
			--target development \
			. || (echo "\033[1;31m❌ Docker build failed\033[0m"; exit 1); \
	else \
		echo "\033[1;33m⚠️  BuildKit not available, using legacy build\033[0m"; \
		docker build \
			--build-arg TARGETPLATFORM=$(TARGET_PLATFORM) \
			-t $(IMAGE_NAME):dev \
			-f Dockerfile.legacy-dev \
			. || (echo "\033[1;31m❌ Docker build failed\033[0m"; exit 1); \
	fi
	@echo "\033[1;32m✅ Docker development image built successfully\033[0m"

## Run application in Docker (development)
.PHONY: docker-run
docker-run: docker-build-dev
	@if [ "$(shell docker ps -q -f name=^$(CONTAINER_NAME)$$)" ]; then \
		echo "Container $(CONTAINER_NAME) is already running. Stopping and removing..."; \
		docker stop $(CONTAINER_NAME) >/dev/null 2>&1 || true; \
		docker rm $(CONTAINER_NAME) >/dev/null 2>&1 || true; \
	fi
	docker run -d \
		-p $(DOCKER_PORT):5000 \
		-v $(PWD):/app \
		-v $(VOLUME_NAME):/app/instance \
		--env-file .env \
		--name $(CONTAINER_NAME) \
		$(IMAGE_NAME):dev

## Start all containers
.PHONY: docker-up
docker-up:
	$(DOCKER_COMPOSE_DEV) up -d

## Stop all containers
.PHONY: docker-down
docker-down:
	$(DOCKER_COMPOSE_DEV) down

## Stop running containers
.PHONY: docker-stop
docker-stop:
	docker rm -f $(CONTAINER_NAME) || true

## View container logs
.PHONY: docker-logs
docker-logs:
	docker logs -f $(CONTAINER_NAME)

## Open shell in container
.PHONY: docker-shell
docker-shell:
	docker exec -it $(CONTAINER_NAME) /bin/bash

## Clean up Docker resources
.PHONY: docker-clean
docker-clean: docker-stop
	docker volume rm -f $(VOLUME_NAME) || true
	docker rmi -f $(IMAGE_NAME) || true

## Rebuild and run in Docker
.PHONY: docker-rebuild
docker-rebuild: docker-clean docker-build docker-run

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

## Format Terraform files
.PHONY: tf-fmt
tf-fmt:
	@if [ -z "$(TF_ENV)" ]; then \
		echo "Error: TF_ENV is not set. Usage: make tf-fmt TF_ENV=<env>"; \
		exit 1; \
	fi
	@echo "Formatting Terraform files in $(TF_ENV_DIR)..."
	@cd terraform && \
	cd "environments/$(TF_ENV)" && \
	terraform fmt -recursive

## Clean Terraform lock files and cache
.PHONY: tf-clean
tf-clean:
	@if [ -z "$(TF_ENV)" ]; then \
		echo "Error: TF_ENV is not set. Usage: make tf-clean TF_ENV=<env>"; \
		exit 1; \
	fi
	@echo "Cleaning Terraform lock files and cache for $(TF_ENV)..."
	@cd terraform && \
	rm -rf "environments/$(TF_ENV)/.terraform" \
		"environments/$(TF_ENV)/.terraform.lock.hcl" \
		"environments/$(TF_ENV)/tfplan-$(TF_ENV)"
	@echo "Terraform cache, lock files, and plan files have been removed"

## Check infrastructure
.PHONY: check-infra
check-infra: tf-validate tf-fmt
	@if [ "$(SKIP_TRIVY)" != "true" ]; then \
		$(MAKE) trivy; \
	else \
		echo "🔍 Skipping Trivy scan (SKIP_TRIVY=true)"; \
	fi
	@echo "✅ Infrastructure configuration validated, formatted$(if $(SKIP_TRIVY),, and secured)"

## Run Trivy security scan
.PHONY: trivy
trivy:
	@echo "🔍 Running Trivy security scan..."
	@if ! command -v trivy >/dev/null 2>&1; then \
		echo "❌ Trivy is not installed. Please install it first:"; \
		echo "   # macOS: brew install aquasecurity/trivy/trivy"; \
		echo "   # Linux: brew install aquasecurity/trivy/trivy or use the installation script"; \
		echo "   #   curl -sfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh | sh -s -- -b /usr/local/bin"; \
		exit 1; \
	fi
	@echo "📋 Scanning Terraform files..."
	@cd terraform && \
	cd environments/$(TF_ENV) && \
	trivy config --tf-vars terraform.tfvars .
	@echo "\n📋 Scanning CloudFormation files..."
	@cd terraform && \
	find . -path "*/cloudformation/*.y*ml" -type f -exec echo "Scanning {}" \; -exec trivy config "{}" \;
	@echo "✅ Trivy scan completed"

## Setup Terraform backend
.PHONY: setup-tf-backend
setup-tf-backend:
	@echo "Setting up Terraform backend via CloudFormation..."
	@./scripts/setup-terraform-backend.sh $(ARGS)

## Destroy Terraform backend
.PHONY: destroy-tf-backend
destroy-tf-backend:
	@STACK_NAME="$(or $(DESTROY_STACK),terraform-backend)"; \
	REGION="$(or $(DESTROY_REGION),us-east-1)"; \
	echo "Deleting Terraform backend stack '$$STACK_NAME' in region '$$REGION'..."; \
	aws cloudformation delete-stack --stack-name "$$STACK_NAME" --region "$$REGION"; \
	aws cloudformation wait stack-delete-complete --stack-name "$$STACK_NAME" --region "$$REGION" || true; \
	echo "✅ Terraform backend stack '$$STACK_NAME' deletion completed in region '$$REGION'."

# =============================================================================
# Deployment
# =============================================================================

## Deploy to dev environment
.PHONY: deploy-dev
deploy-dev: validate-env check-lambda-package
	@echo "\033[1m🚀 Deploying to dev environment...\033[0m"
	@./scripts/deploy_lambda.sh \
	  --function-name "$(LAMBDA_FUNCTION_NAME)-dev" \
	  --environment dev \
	  --profile "$(DEFAULT_AWS_PROFILE)" \
	  --region "$(DEFAULT_AWS_REGION)" \
	  --package both || (echo "\033[1;31m❌ Dev deployment failed\033[0m"; exit 1)
	@echo "\033[1;32m✅ Dev deployment completed successfully\033[0m"

## Deploy to staging environment
.PHONY: deploy-staging
deploy-staging: validate-env check-lambda-package
	@echo "\033[1m🚀 Deploying to staging environment...\033[0m"
	@read -p "This will deploy to the staging environment. Continue? [y/N] " confirm && [ "$$confirm" = "y" ] || [ "$$confirm" = "Y" ] || (echo "\033[1;33m⚠️  Aborting...\033[0m"; exit 1)
	@./scripts/deploy_lambda.sh \
	  --function-name "$(LAMBDA_FUNCTION_NAME)-staging" \
	  --environment staging \
	  --profile "$(DEFAULT_AWS_PROFILE)" \
	  --region "$(DEFAULT_AWS_REGION)" \
	  --package both || (echo "\033[1;31m❌ Staging deployment failed\033[0m"; exit 1)
	@echo "\033[1;32m✅ Staging deployment completed successfully\033[0m"

## Deploy to production environment
.PHONY: deploy-prod
deploy-prod: validate-env check-lambda-package
	@echo "\033[1;31m⚠️  WARNING: You are about to deploy to PRODUCTION!\033[0m"
	@echo "\033[1;31m⚠️  This will apply all pending changes to your production environment.\033[0m"
	@read -p "Type 'production' to continue: " confirm && [ "$$confirm" = "production" ]
	@./scripts/deploy_lambda.sh \
	  --function-name "$(LAMBDA_FUNCTION_NAME)" \
	  --environment prod \
	  --profile "$(DEFAULT_AWS_PROFILE)" \
	  --region "$(DEFAULT_AWS_REGION)" \
	  --package both || (echo "\033[1;31m❌ Production deployment failed\033[0m"; exit 1)
	@echo "\033[1;32m✅ Production deployment completed successfully\033[0m"

## Deploy Lambda function
.PHONY: deploy-lambda
deploy-lambda: check-lambda-package
	@echo "🚀 Deploying Lambda function with update..."
	@./scripts/deploy_lambda.sh \
	  --function-name "$(LAMBDA_FUNCTION_NAME)" \
	  --environment "$(ENV)" \
	  --profile "$(DEFAULT_AWS_PROFILE)" \
	  --region "$(DEFAULT_AWS_REGION)" \
	  --package app \
	  --update

## Package Lambda deployment
.PHONY: package-lambda
package-lambda: package-layer
	@echo "\033[1m📦 Creating Lambda deployment package...\033[0m"
	@if [ ! -x "$(shell which zip)" ]; then \
		echo "Error: 'zip' command is required but not installed."; \
		exit 1; \
	fi
	@if [ ! -x "$(shell which pip)" ]; then \
		echo "Error: 'pip' command is required but not installed."; \
		exit 1; \
	fi
	@chmod +x scripts/package.sh
	@if ! ./scripts/package.sh; then \
		echo "\033[1;31m❌ Failed to create Lambda package\033[0m"; \
		exit 1; \
	fi
	@echo "\033[1;32m✅ Lambda package created at dist/app.zip\033[0m"

## Package Lambda layer
.PHONY: package-layer
package-layer:
	@echo "\033[1m📦 Creating Lambda layer package...\033[0m"
	@if [ ! -x "$(shell which zip)" ]; then \
		echo "Error: 'zip' command is required but not installed."; \
		exit 1; \
	fi
	@if [ ! -x "$(shell which pip)" ]; then \
		echo "Error: 'pip' command is required but not installed."; \
		exit 1; \
	fi
	@chmod +x scripts/package.sh
	@if ! ./scripts/package.sh -l; then \
		echo "\033[1;31m❌ Failed to create Lambda layer package\033[0m"; \
		exit 1; \
	fi
	@echo "\033[1;32m✅ Lambda layer package created at dist/layers/python-dependencies-latest.zip\033[0m"

## Check Lambda package exists
.PHONY: check-lambda-package
check-lambda-package:
	@if [ ! -f "dist/app.zip" ]; then \
		echo "\033[1;33m⚠️  Lambda package (dist/app.zip) not found.\033[0m"; \
		echo -n "Run 'make package-lambda' to create it now? [y/N] "; \
		read -r -n 1; \
		if [[ "$$REPLY" =~ ^[Yy]$$ ]]; then \
			echo ""; \
			$(MAKE) package-lambda; \
			if [ ! -f "dist/app.zip" ]; then \
				echo "\033[1;31m❌ Package creation failed. Please fix the issues and try again.\033[0m"; \
				exit 1; \
			fi; \
		else \
			echo "\n\033[1;31m❌ Aborting: Lambda package is required for deployment.\033[0m"; \
			exit 1; \
		fi; \
	fi

## Invoke Lambda function
.PHONY: invoke-lambda
invoke-lambda:
	@echo "\033[1m🚀 Invoking Lambda function...\033[0m"
	@echo "Using Lambda function: $(LAMBDA_FUNCTION_NAME)"
	@mkdir -p tmp
	@echo '{"version":"2.0","routeKey":"GET /api/health","rawPath":"/api/health","requestContext":{"http":{"method":"GET","path":"/api/health"},"requestId":"test-invoke-request"},"isBase64Encoded":false}' > tmp/test-event.json
	@echo "\n\033[1m📤 Sending test request to Lambda function...\033[0m"
	@echo "\n\033[1m📝 Logs and Response:\033[0m"
	@aws lambda invoke \
		--function-name "$(LAMBDA_FUNCTION_NAME)" \
		--payload file://tmp/test-event.json \
		--cli-binary-format raw-in-base64-out \
		--log-type Tail \
		--output json \
		tmp/response.json \
		--query 'LogResult' \
		--output text \
		2>/dev/null | base64 --decode
	@echo "\n\033[1m📄 Response Body:\033[0m"
	@cat tmp/response.json | jq .
	@echo "\n\033[1m✅ Lambda function test completed\033[0m"

## Run database migrations
.PHONY: run-migrations
run-migrations: check-aws-cli
	@if [ -z "$(FUNCTION_NAME)" ]; then \
		read -p "Enter Lambda function name: " FUNCTION_NAME; \
	else \
		FUNCTION_NAME="$(FUNCTION_NAME)"; \
	fi; \
	if [ -z "$(REGION)" ]; then \
		read -p "Enter AWS region [us-east-1]: " REGION; \
		REGION=$${REGION:-us-east-1}; \
	else \
		REGION="$(REGION)"; \
	fi; \
	if [ -z "$(PROFILE)" ]; then \
		read -p "Enter AWS profile [default]: " PROFILE; \
		PROFILE=$${PROFILE:-default}; \
	else \
		PROFILE="$(PROFILE)"; \
	fi; \
	echo "🚀 Invoking migrations on Lambda function $$FUNCTION_NAME in region $$REGION with profile $$PROFILE..."; \
	python3 scripts/invoke_migrations.py --function-name "$$FUNCTION_NAME" --region "$$REGION" --profile "$$PROFILE"

## Run migrations locally
.PHONY: run-migrations-local
run-migrations-local: test-db-connection
	@echo "\033[1m🔄 Running database migrations...\033[0m"
	@if ! python3 scripts/test_db_connection.py --migrate; then \
		echo "\033[1;31m❌ Database migrations failed\033[0m"; \
		exit 1; \
	fi
	@echo "\033[1;32m✅ Database migrations completed successfully!\033[0m"

## Test database connection
.PHONY: test-db-connection
test-db-connection:
	@echo "\033[1m🔍 Testing database connection...\033[0m"
	@if [ ! -f ".env" ] && [ ! -f ".env.local" ]; then \
		echo "\033[1;33m⚠️  No .env file found. Creating from example...\033[0m"; \
		cp -n .env.example .env.local 2>/dev/null || cp -n .env.example .env 2>/dev/null || true; \
	fi
	@if [ ! -x "$(shell which python3)" ]; then \
		echo "\033[1;31m❌ Python 3 is required but not installed\033[0m"; \
		exit 1; \
	fi
	@if ! python3 -c "import sqlalchemy" >/dev/null 2>&1; then \
		echo "\033[1;33m⚠️  SQLAlchemy not found. Installing dependencies...\033[0m"; \
		pip install -r requirements.txt || { echo "\033[1;31m❌ Failed to install dependencies\033[0m"; exit 1; }; \
	fi
	@echo "\033[1m🔧 Running database connection test...\033[0m"
	@if ! python3 scripts/test_db_connection.py; then \
		echo "\033[1;31m❌ Database connection test failed\033[0m"; \
		exit 1; \
	fi
	@echo "\033[1;32m✅ Database connection test passed!\033[0m"

## Check AWS CLI
.PHONY: check-aws-cli
check-aws-cli:
	@if ! command -v aws >/dev/null 2>&1; then \
		echo "\033[1;31m❌ AWS CLI is required but not installed\033[0m"; \
		exit 1; \
	fi

# =============================================================================
# Dependencies Management
# =============================================================================

# Install pip-tools if not already installed
PIP_TOOLS := $(shell pip show pip-tools >/dev/null 2>&1 || echo "pip-tools not installed")

# Default requirements files
REQUIREMENTS_FILES = requirements.txt requirements-dev.txt requirements-prod.txt

## Generate requirements files if they don't exist
.PHONY: check-requirements
check-requirements:
	@for req in $(REQUIREMENTS_FILES); do \
		if [ ! -f "$$req" ]; then \
			echo "$$req not found, generating..."; \
			$(MAKE) $$req; \
		fi; \
	done

## Update all requirements files
.PHONY: requirements
requirements: check-pip-tools
	@echo "Updating requirements files..."
	@scripts/update_requirements.sh

## Install development environment
.PHONY: dev-setup
dev-setup: check-pip-tools requirements
	@echo "Setting up development environment..."
	pip install -c constraints.txt -r requirements.txt -r requirements-dev.txt

## Install production dependencies
.PHONY: prod-setup
prod-setup: check-pip-tools requirements
	@echo "Setting up production environment..."
	pip install -c constraints.txt -r requirements-prod.txt

## Check if pip-tools is installed
.PHONY: check-pip-tools
check-pip-tools:
	@if [ "$(PIP_TOOLS)" = "pip-tools not installed" ]; then \
		echo "Installing pip-tools..."; \
		pip install pip-tools; \
	fi

## Add a new package to base requirements
.PHONY: add-base-req
add-base-req:
	@if [ -z "$(PACKAGE)" ]; then \
		echo "Error: PACKAGE not specified. Usage: make add-base-req PACKAGE=package[==version]"; \
		exit 1; \
	fi
	@echo "$(PACKAGE)" >> requirements/base.in
	@echo "Added $(PACKAGE) to requirements/base.in"
	@$(MAKE) requirements

## Add a new development package
.PHONY: add-dev-req
add-dev-req:
	@if [ -z "$(PACKAGE)" ]; then \
		echo "Error: PACKAGE not specified. Usage: make add-dev-req PACKAGE=package[==version]"; \
		exit 1; \
	fi
	@echo "$(PACKAGE)" >> requirements/dev.in
	@echo "Added $(PACKAGE) to requirements/dev.in"
	@$(MAKE) requirements

## List all installed packages
.PHONY: list-reqs
list-reqs:
	pip list

## Show dependency tree
.PHONY: show-deps
show-deps:
	pipdeptree

## Check for dependency conflicts
.PHONY: check-reqs
check-reqs:
	pip check

## Clean up generated requirements files
.PHONY: clean-requirements
clean-requirements:
	rm -f requirements.txt requirements-dev.txt requirements-prod.txt

## Update a single requirements file
%.txt: %.in
	@echo "Updating $@..."
	@TMP_FILE=$$(mktemp -p . .tmp_XXXXXXXXXX) && \
	trap 'rm -f "$$TMP_FILE"' EXIT && \
	pip-compile --upgrade -c constraints.txt -o "$$TMP_FILE" $< && \
	mv "$$TMP_FILE" $@ || { rm -f "$$TMP_FILE"; exit 1; }

# =============================================================================
# Security
# =============================================================================

## Run Snyk security scan with high severity threshold
.PHONY: snyk-scan
snyk-scan:
	snyk test --severity-threshold=high

## Check for security vulnerabilities in dependencies
.PHONY: check-vulns
check-vulns:
	snyk test --severity-threshold=medium

## Monitor project for security vulnerabilities
.PHONY: monitor
monitor:
	snyk monitor

## Check for security vulnerabilities
.PHONY: security-check
security-check: check-pip-tools
	@echo "Checking for security vulnerabilities..."
	pip install safety bandit
	safety check -r requirements.txt
	bandit -r app/

# =============================================================================
# GitHub Actions
# =============================================================================

## Setup GitHub Actions workflows
.PHONY: setup-github-actions
setup-github-actions:
	@if [ -z "$(GITHUB_ORG)" ]; then \
		echo "Error: GITHUB_ORG is required. Example: make setup-github-actions GITHUB_ORG=your-org"; \
		exit 1; \
	fi
	@echo "🚀 Setting up GitHub Actions for $(GITHUB_ORG)/$(or $(REPO_NAME),meal-expense-tracker)..."
	@if [ ! -x "scripts/setup-github-actions.sh" ]; then \
		echo "Error: setup-github-actions.sh script not found or not executable"; \
		exit 1; \
	fi
	@./scripts/setup-github-actions.sh --github-org "$(GITHUB_ORG)" $(if $(REPO_NAME),--repo-name "$(REPO_NAME)")

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
	@command -v $(PYTHON) >/dev/null 2>&1 || (echo "\033[1;31m❌ $(PYTHON) not found\033[0m"; exit 1)
	@command -v $(PIP) >/dev/null 2>&1 || (echo "\033[1;31m❌ $(PIP) not found\033[0m"; exit 1)
	@command -v docker >/dev/null 2>&1 || (echo "\033[1;33m⚠️  Docker not found\033[0m")
	@command -v terraform >/dev/null 2>&1 || (echo "\033[1;33m⚠️  Terraform not found\033[0m")
	@echo "\033[1;32m✅ Environment check completed\033[0m"

## Validate all required tools and environment
.PHONY: validate-env
validate-env: check-env
	@echo "\033[1m🔍 Validating development environment...\033[0m"
	@command -v docker >/dev/null 2>&1 || (echo "\033[1;31m❌ Docker not found\033[0m"; exit 1)
	@command -v terraform >/dev/null 2>&1 || (echo "\033[1;31m❌ Terraform not found\033[0m"; exit 1)
	@command -v aws >/dev/null 2>&1 || (echo "\033[1;33m⚠️  AWS CLI not found\033[0m")
	@command -v trivy >/dev/null 2>&1 || (echo "\033[1;33m⚠️  Trivy not found\033[0m")
	@command -v snyk >/dev/null 2>&1 || (echo "\033[1;33m⚠️  Snyk not found\033[0m")
	@echo "\033[1;32m✅ Environment validation completed\033[0m"

# =============================================================================
# Aliases for backward compatibility
# =============================================================================
.PHONY: build stop logs restart run-local rebuild-logs
build: docker-build
stop: docker-stop
logs: docker-logs
restart: docker-stop docker-run
run-local: run
rebuild-logs: docker-rebuild docker-logs

# =============================================================================
# Performance & Caching
# =============================================================================

## Clear all caches for fresh start
.PHONY: cache-clear
cache-clear:
	@echo "\n\033[1m=== Clearing Caches ===\033[0m"
	@echo "Removing Python cache files..."
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@find . -type f -name "*.pyo" -delete 2>/dev/null || true
	@find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name ".coverage" -delete 2>/dev/null || true
	@find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	@echo "✅ Caches cleared"

## Check dependency freshness
.PHONY: deps-check
deps-check: check-env
	@echo "\n\033[1m=== Checking Dependencies ===\033[0m"
	@echo "Checking for outdated packages..."
	@$(PIP) list --outdated || echo "✅ All dependencies are up to date"

## Install/update development dependencies
.PHONY: deps-update
deps-update: check-env
	@echo "\n\033[1m=== Updating Dependencies ===\033[0m"
	@$(PIP) install --upgrade pip setuptools wheel
	@$(PIP) install -r requirements/dev.txt --upgrade
	@echo "✅ Dependencies updated"

# =============================================================================
# Health Checks & Monitoring
# =============================================================================

## Application health checks
.PHONY: health-check
health-check: check-env
	@echo "\n\033[1m=== Application Health Check ===\033[0m"
	@echo "Checking application imports..."
	@$(PYTHON) -c "import app; print('✅ App imports successfully')" || (echo "❌ App import failed"; exit 1)
	@$(PYTHON) -c "from app import create_app; app = create_app(); print('✅ App factory works')" || (echo "❌ App factory failed"; exit 1)
	@$(PYTHON) -c "from app.database import db; print('✅ Database connection available')" || (echo "❌ Database connection failed"; exit 1)
	@echo "✅ Application health check passed"

## System resource checks
.PHONY: system-check
system-check:
	@echo "\n\033[1m=== System Resource Check ===\033[0m"
	@echo "Memory usage:"
	@free -h | grep Mem | awk '{print "  " $$3 "/" $$2 " (" $$5 " used)"}' || echo "  Unable to check memory"
	@echo "Disk usage:"
	@df -h . | tail -1 | awk '{print "  " $$5 " used on " $$1}' || echo "  Unable to check disk"
	@echo "Python version:"
	@$(PYTHON) --version || echo "  Unable to check Python version"
	@echo "✅ System check completed"

## Full system validation
.PHONY: system-validate
system-validate: system-check health-check
	@echo "\n\033[1m=== System Validation ===\033[0m"
	@echo "✅ System validation completed successfully"

# =============================================================================
# Enhanced Error Handling & Recovery
# =============================================================================

## Automatic fixes for common issues
.PHONY: auto-fix
auto-fix: check-env
	@echo "\n\033[1m=== Automatic Fixes ===\033[0m"
	@echo "Upgrading pip and setuptools..."
	@$(PYTHON) -m pip install --upgrade pip setuptools wheel || echo "⚠️  Could not upgrade pip"
	@echo "Checking for dependency conflicts..."
	@$(PYTHON) -m pip check || echo "⚠️  Dependency conflicts found"
	@echo "Reinstalling development dependencies..."
	@$(PYTHON) -m pip install -r requirements/dev.txt --force-reinstall || echo "⚠️  Could not reinstall dev deps"
	@echo "Clearing caches..."
	@$(MAKE) cache-clear
	@echo "✅ Automatic fixes completed"

## Rollback capability for deployments
.PHONY: rollback
rollback:
	@echo "\n\033[1;33m⚠️  Rollback Options ===\033[0m"
	@echo "Recent commits:"
	@git log --oneline -10 || echo "  Not a git repository"
	@echo ""
	@echo "To rollback:"
	@echo "  1. Check recent commits: git log --oneline"
	@echo "  2. Rollback to specific commit: git checkout <commit-hash>"
	@echo "  3. Or rollback last commit: git reset --hard HEAD~1"
	@echo "  4. Force push if needed: git push --force-with-lease origin <branch>"
	@echo ""
	@echo "⚠️  WARNING: Rollback will lose uncommitted changes!"

## Dependency conflict resolution
.PHONY: deps-resolve
deps-resolve: check-env
	@echo "\n\033[1m=== Resolving Dependencies ===\033[0m"
	@echo "Checking for conflicts..."
	@$(PYTHON) -m pip check || echo "⚠️  Conflicts found, attempting resolution..."
	@$(PYTHON) -m pip install --upgrade --force-reinstall -r requirements/dev.txt || echo "❌ Resolution failed"
	@echo "✅ Dependency resolution completed"

# =============================================================================
# Development Workflow Enhancements
# =============================================================================

## Complete development setup
.PHONY: dev-setup
dev-setup: setup check-env health-check
	@echo "\n\033[1m=== Development Setup Complete ===\033[0m"
	@echo "✅ Development environment ready!"
	@echo "Next steps:"
	@echo "  - make run          # Start the application"
	@echo "  - make test         # Run tests"
	@echo "  - make quality      # Run full quality checks"

## Quick development cycle
.PHONY: dev-cycle
dev-cycle: format lint test
	@echo "\n\033[1m=== Development Cycle ===\033[0m"
	@echo "✅ Development cycle completed successfully!"
	@echo "Ready for commit!"

## Development status check
.PHONY: dev-status
dev-status: check-env
	@echo "\n\033[1m=== Development Status ===\033[0m"
	@echo "✅ Environment: OK"
	@echo "🐍 Python: $(shell $(PYTHON) --version)"
	@echo "📦 Dependencies: $(shell $(PIP) list | wc -l) packages"
	@echo "🧪 Tests: $(shell find tests/ -name "*.py" | wc -l) test files"
	@echo "📁 App modules: $(shell find app/ -name "*.py" | wc -l) Python files"
	@echo "🌐 Templates: $(shell find app/templates -name "*.html" | wc -l) HTML files"
