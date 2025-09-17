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
	@echo "  \033[1mmake setup\033[0m           Install development dependencies"
	@echo "  \033[1mmake run\033[0m             Run the application locally"
	@echo "  \033[1mmake format\033[0m          Format code with black and autoflake"
	@echo "  \033[1mmake lint\033[0m            Run linters (flake8, black, mypy)"
	@echo "  \033[1mmake test\033[0m            Run all tests with coverage"
	@echo "  \033[1mmake check\033[0m           Run all checks (format + lint + test)"
	@echo "  \033[1mmake pre-commit\033[0m      Run pre-commit checks"
	@echo "  \033[1mmake validate-env\033[0m    Validate development environment"

	@echo "\n\033[1mLocal CI/CD:\033[0m"
	@echo "  \033[1mmake ci-local\033[0m        Run local CI workflow (equivalent to ci.yml)"
	@echo "  \033[1mmake ci-quick\033[0m        Run quick CI checks (lint + unit tests)"
	@echo "  \033[1mmake pipeline-local\033[0m  Run local pipeline workflow (equivalent to deploy.yml)"
	@echo "  \033[1mmake act-ci\033[0m          Run CI workflow using act"
	@echo "  \033[1mmake act-deploy\033[0m      Run deploy workflow using act"
	@echo "  \033[1mmake act-release\033[0m     Run release workflow using act"

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

	@echo "\n\033[1mTerraform (TF_ENV=env, default: dev):\033[0m"
	@echo "  \033[1mmake tf-init\033[0m        Initialize Terraform with backend config"
	@echo "  \033[1mmake tf-plan\033[0m        Generate and show execution plan"
	@echo "  \033[1mmake tf-apply\033[0m       Apply changes to infrastructure"
	@echo "  \033[1mmake tf-destroy\033[0m     Destroy infrastructure"
	@echo "  \033[1mmake tf-validate\033[0m    Validate Terraform configuration"

	@echo "\n\033[1mDeployment Pipeline:\033[0m"
	@echo "  \033[1mmake deploy-dev\033[0m      Deploy to development environment"
	@echo "  \033[1mmake deploy-staging\033[0m  Deploy to staging environment"
	@echo "  \033[1mmake deploy-prod\033[0m     Deploy to production environment"
	@echo "  \033[1mmake release-staging\033[0m Release to staging (tag-based)"
	@echo "  \033[1mmake release-prod\033[0m    Release to production (tag-based)"

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
lint: lint-python

## Python linter
.PHONY: lint-python
lint-python: check-env
	@echo "\n\033[1m=== Running Python Linter ===\033[0m"
	@$(PYTHON) -m flake8 app tests || (echo "\033[1;31m❌ Flake8 failed\033[0m"; exit 1)
	@$(PYTHON) -m black --check app tests || (echo "\033[1;31m❌ Black check failed\033[0m"; exit 1)

## Format all code (Python)
.PHONY: format
format: format-python

## Format Python code
.PHONY: format-python
format-python: check-env
	@echo "\n\033[1m=== Formatting Python code ===\033[0m"
	@$(PYTHON) -m isort app/ tests/ migrations/ *.py || (echo "\033[1;31m❌ isort failed\033[0m"; exit 1)
	@$(PYTHON) -m black app/ tests/ migrations/ */*.py *.py || (echo "\033[1;31m❌ black failed\033[0m"; exit 1)
	@$(PYTHON) -m autoflake --in-place --remove-all-unused-imports --recursive app/ tests/ || (echo "\033[1;31m❌ autoflake failed\033[0m"; exit 1)

## Run all tests
.PHONY: test
test: check-env
	@echo "\n\033[1m=== Running Tests ===\033[0m"
	PYTHONPATH=. $(PYTHON) -m pytest tests/ $(PYTEST_OPTS) || (echo "\033[1;31m❌ Tests failed\033[0m"; exit 1)

## Run pre-commit checks
.PHONY: pre-commit
pre-commit: format lint test

## Run all checks (format + lint + test)
.PHONY: check
check: format lint test

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
ci-quick: check-env
	@echo "\n\033[1m=== Running Quick CI Checks ===\033[0m"
	@$(PYTHON) -m flake8 app tests || (echo "\033[1;31m❌ Flake8 failed\033[0m"; exit 1)
	@$(PYTHON) -m black --check app tests || (echo "\033[1;31m❌ Black check failed\033[0m"; exit 1)
	@PYTHONPATH=. $(PYTHON) -m pytest tests/unit/ $(PYTEST_OPTS) || (echo "\033[1;31m❌ Unit tests failed\033[0m"; exit 1)
	@echo "\033[1;32m✅ Quick CI checks completed\033[0m"

## Run local pipeline workflow (equivalent to deploy.yml)
.PHONY: pipeline-local
pipeline-local: check-env
	@echo "\n\033[1m=== Running Local Deploy Workflow ===\033[0m"
	@./scripts/local-pipeline.sh $(ENV) $(SKIP_TESTS)

## Run CI workflow using act
.PHONY: act-ci
act-ci: check-act
	@echo "\n\033[1m=== Running CI Workflow with act ===\033[0m"
	@act -W .github/workflows/ci.yml --secret-file .env.local

## Run deploy workflow using act
.PHONY: act-deploy
act-deploy: check-act
	@echo "\n\033[1m=== Running Deploy Workflow with act ===\033[0m"
	@act -W .github/workflows/deploy.yml --secret-file .env.local --input environment=$(ENV) --input skip_tests=$(SKIP_TESTS)

## Run release workflow using act
.PHONY: act-release
act-release: check-act
	@echo "\n\033[1m=== Running Release Workflow with act ===\033[0m"
	@act -W .github/workflows/release.yml --secret-file .env.local --input environment=$(ENV) --input tag=$(TAG)

## Check if act is installed
.PHONY: check-act
check-act:
	@if command -v act >/dev/null 2>&1; then \
		echo "\033[1;32m✅ act is available\033[0m"; \
	elif [ -f "$$HOME/.local/bin/act" ]; then \
		echo "\033[1;33m⚠️  act found in ~/.local/bin but not in PATH\033[0m"; \
		echo "\033[1;33m   Run: export PATH=\"$$HOME/.local/bin:$$PATH\"\033[0m"; \
		echo "\033[1;33m   Or restart your shell\033[0m"; \
		exit 1; \
	else \
		echo "\033[1;31m❌ act not found. Install with:\033[0m"; \
		echo "\033[1;31m   curl https://raw.githubusercontent.com/nektos/act/master/install.sh | bash -s -- -b ~/.local/bin\033[0m"; \
		echo "\033[1;31m   export PATH=\"$$HOME/.local/bin:$$PATH\"\033[0m"; \
		exit 1; \
	fi

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
	@echo "\033[1;32m✅ Docker image built successfully\033[0m"

## Quick development build
.PHONY: docker-dev
docker-dev: TARGET=development TAG=dev
docker-dev: docker-build

## Quick production build
.PHONY: docker-prod
docker-prod: TARGET=production TAG=prod
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

## Package Lambda deployment
.PHONY: package-lambda
package-lambda:
	@echo "\033[1m📦 Creating Lambda deployment package...\033[0m"
	@if [ ! -x "$(shell which zip)" ]; then \
		echo "Error: 'zip' command is required but not installed."; \
		exit 1; \
	fi
	@chmod +x scripts/package.sh
	@if ! ./scripts/package.sh; then \
		echo "\033[1;31m❌ Failed to create Lambda package\033[0m"; \
		exit 1; \
	fi
	@echo "\033[1;32m✅ Lambda package created at dist/app.zip\033[0m"

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
