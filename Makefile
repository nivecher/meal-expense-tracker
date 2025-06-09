# Meal Expense Tracker - Makefile
# =============================
# 
# Available commands (run 'make help' for details):
#   Development:   setup, run, test, lint, format, db-* 
#   Docker:       docker-{build,run,stop,logs,clean}
#   Terraform:    tf-{init,plan,apply,destroy,validate,fmt,backend}
#   Deployment:   deploy-{dev,staging,prod}
#   Dependencies: requirements, {add,remove,list,show}-reqs
#   Testing:      test, load-test
#   Utilities:    help, clean, check-infra

# =======================
# Configuration
# =======================

# Application settings
APP_NAME = meal-expense-tracker
PORT = 5000
PYTHON = python3
PIP = pip3

# Docker settings
CONTAINER_NAME = $(APP_NAME)-app
IMAGE_NAME = $(APP_NAME)
VOLUME_NAME = $(APP_NAME)-db

# Environment settings
ENV ?= dev
TF_ENV ?= $(ENV)
TF_CMD = cd terraform && make ENV=$(TF_ENV)

# Python settings
PYTHONPATH = $(shell pwd)
FLASK_APP = wsgi.py
FLASK_ENV = development

# Enable BuildKit for better build performance and features
export DOCKER_BUILDKIT=1
export PYTHONPATH

# =======================
# Help
# =======================

## Display comprehensive help
.PHONY: help
help:
	@echo "\n\033[1mMeal Expense Tracker - Available Commands:\033[0m"
	
	@echo "\n\033[1;34mDevelopment:\033[0m"
	@echo "  \033[1mmake setup\033[0m           Install development dependencies"
	@echo "  \033[1mmake run\033[0m             Run the application locally"
	@echo "  \033[1mmake test\033[0m            Run tests"
	@echo "  \033[1mmake lint\033[0m            Run linters (flake8, black in check mode)"
	@echo "  \033[1mmake format\033[0m          Format code with black and autoflake"
	@echo "  \033[1mmake check-infra\033[0m     Validate Terraform configuration"

	@echo "\n\033[1;34mDatabase:\033[0m"
	@echo "  \033[1mmake db-init\033[0m         Initialize database"
	@echo "  \033[1mmake db-migrate\033[0m      Create new database migration"
	@echo "  \033[1mmake db-upgrade\033[0m      Upgrade database to latest migration"
	@echo "  \033[1mmake db-downgrade\033[0m    Downgrade database by one migration"

	@echo "\n\033[1;34mDocker:\033[0m"
	@echo "  \033[1mmake docker-build\033[0m    Build Docker image"
	@echo "  \033[1mmake docker-run\033[0m      Run application in Docker"
	@echo "  \033[1mmake docker-stop\033[0m     Stop running containers"
	@echo "  \033[1mmake docker-logs\033[0m     View container logs (follow mode)"
	@echo "  \033[1mmake docker-clean\033[0m    Remove containers, volumes, and images"
	@echo "  \033[1mmake docker-rebuild\033[0m  Rebuild and run in Docker"

	@echo "\n\033[1;34mTerraform (TF_ENV=env, default: dev):\033[0m"
	@echo "  \033[1mmake tf-init\033[0m        Initialize Terraform with backend config"
	@echo "  \033[1mmake tf-plan\033[0m        Generate and show execution plan"
	@echo "  \033[1mmake tf-apply\033[0m       Apply changes to infrastructure"
	@echo "  \033[1mmake tf-destroy\033[0m     Destroy infrastructure"
	@echo "  \033[1mmake tf-validate\033[0m    Validate Terraform configuration"
	@echo "  \033[1mmake tf-fmt\033[0m         Format Terraform files"
	@echo "  \033[1mmake tf-backend\033[0m     Configure Terraform backend"

	@echo "\n\033[1;34mDeployment:\033[0m"
	@echo "  \033[1mmake deploy-dev\033[0m      Deploy to development environment"
	@echo "  \033[1mmake deploy-staging\033[0m  Deploy to staging environment"
	@echo "  \033[1mmake deploy-prod\033[0m     Deploy to production environment"

	@echo "\n\033[1;34mDependencies:\033[0m"
	@echo "  \033[1mmake requirements\033[0m    Update requirements files"
	@echo "  \033[1mmake rebuild-reqs\033[0m    Rebuild requirements.txt from requirements.in"
	@echo "  \033[1mmake add-req PACKAGE=name\033[0m  Add a new package to requirements.in"
	@echo "  \033[1mmake remove-req PACKAGE=name\033[0m Remove a package from requirements.in"
	@echo "  \033[1mmake list-reqs\033[0m      List all installed packages"
	@echo "  \033[1mmake show-deps\033[0m      Show dependency tree"
	@echo "  \033[1mmake check-reqs\033[0m     Check for dependency conflicts"

	@echo "\n\033[1;34mTesting:\033[0m"
	@echo "  \033[1mmake test\033[0m            Run all tests"
	@echo "  \033[1mmake load-test\033[0m        Run load tests (not yet implemented)"

	@echo "\n\033[1;34mUtilities:\033[0m"
	@echo "  \033[1mmake clean\033[0m           Remove build artifacts and temporary files"
	@echo "  \033[1mmake help\033[0m            Show this help message"

	@echo "\n\033[1;33mExamples:\033[0m"
	@echo "  \033[1mmake setup && make run\033[0m     # Setup and run locally"
	@echo "  \033[1mmake docker-rebuild\033[0m        # Rebuild and run in Docker"
	@echo "  \033[1mmake tf-init TF_ENV=staging\033[0m # Initialize staging environment"
	@echo "  \033[1mmake deploy-dev\033[0m             # Deploy to development"

# =======================
# Development
# =======================

## Install development dependencies
.PHONY: setup
setup:
	$(PIP) install -r requirements-dev.txt
	$(PIP) install -e .

## Run the application locally
.PHONY: run
run:
	FLASK_APP=$(FLASK_APP) FLASK_ENV=$(FLASK_ENV) flask run --port $(PORT)

## Run linters
.PHONY: lint
lint:
	flake8 app/ tests/
	black --check app/ tests/

## Format code
.PHONY: format
format:
	black app/ tests/
	autoflake --in-place --remove-all-unused-imports --recursive app/ tests/

## Run tests
.PHONY: test
test:
	PYTHONPATH=. pytest tests/

## Run load tests
.PHONY: load-test
load-test:
	@echo "Load testing not yet implemented"

# =======================
# Database
# =======================

## Initialize database
.PHONY: db-init
db-init:
	$(PYTHON) init_db.py

## Run database migrations
.PHONY: db-migrate
db-migrate:
	flask db migrate -m "$(shell date +%Y%m%d_%H%M%S)"

## Upgrade database
.PHONY: db-upgrade
db-upgrade:
	flask db upgrade

## Downgrade database
.PHONY: db-downgrade
db-downgrade:
	flask db downgrade

# =======================
# Docker
# =======================

## Build Docker image
.PHONY: docker-build
docker-build:
	docker build -t $(IMAGE_NAME) .

## Run application in Docker
.PHONY: docker-run
docker-run:
	docker run -d \
		-p $(PORT):$(PORT) \
		-v $(VOLUME_NAME):/app/instance \
		--env-file .env \
		--name $(CONTAINER_NAME) \
		$(IMAGE_NAME)

## Stop running containers
.PHONY: docker-stop
docker-stop:
	docker rm -f $(CONTAINER_NAME) || true

## View container logs
.PHONY: docker-logs
docker-logs:
	docker logs -f $(CONTAINER_NAME)

## Clean up Docker resources
.PHONY: docker-clean
docker-clean: docker-stop
	docker volume rm -f $(VOLUME_NAME) || true
	docker rmi -f $(IMAGE_NAME) || true

## Rebuild and run in Docker
.PHONY: docker-rebuild
docker-rebuild: docker-clean docker-build docker-run

# =======================
# Terraform
# =======================

## Initialize Terraform commands
.PHONY: tf-init tf-plan tf-apply tf-destroy tf-validate tf-fmt tf-backend

tf-init:
	@echo "Initializing Terraform environment: $(TF_ENV)"
	@cd terraform && terraform init \
		-backend-config=backend-$(TF_ENV).hcl

## Generate a plan without applying
tf-plan:
	@echo "Creating Terraform plan for environment: $(TF_ENV)"
	@cd terraform && terraform plan \
		-var-file=$(TF_ENV).tfvars \
		-out=tfplan-$(TF_ENV)

## Apply the most recent plan
tf-apply:
	@echo "Applying Terraform changes to environment: $(TF_ENV)"
	@cd terraform && terraform apply \
		-var-file=$(TF_ENV).tfvars \
		tfplan-$(TF_ENV)

## Destroy all resources in the environment
tf-destroy:
	@echo "Destroying Terraform environment: $(TF_ENV)"
	@echo "WARNING: This will destroy all resources in the $(TF_ENV) environment!"
	@read -p "Are you sure? (y/N) " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		cd terraform && terraform destroy -var-file=$(TF_ENV).tfvars; \
	fi

## Validate Terraform configuration
tf-validate:
	@echo "Validating Terraform configuration..."
	@cd terraform && terraform init -backend=false
	@cd terraform && terraform validate

## Format Terraform files
.PHONY: tf-fmt
tf-fmt:
	@cd terraform && terraform fmt -recursive

## Configure Terraform backend
tf-backend:
	@echo "Configuring Terraform backend for environment: $(TF_ENV)"
	@if [ ! -f "terraform/backend-$(TF_ENV).hcl" ]; then \
		echo "Backend configuration for $(TF_ENV) not found."; \
		echo "Create terraform/backend-$(TF_ENV).hcl with your backend configuration."; \
		exit 1; \
	fi
	@echo "Backend configuration for $(TF_ENV) is ready."

## Check infrastructure
.PHONY: check-infra
check-infra: tf-validate tf-fmt tfsec
	@echo "✅ Infrastructure configuration validated, formatted, and secured"

## Run TFSec security scan
.PHONY: tfsec
tfsec:
	@echo "🔍 Running TFSec security scan..."
	@if ! command -v tfsec >/dev/null 2>&1; then \
		echo "❌ TFSec is not installed. Please install it first:"; \
		echo "   # macOS: brew install tfsec"; \
		echo "   # Linux: curl -s https://raw.githubusercontent.com/aquasecurity/tfsec/master/scripts/install_linux.sh | bash"; \
		exit 1; \
	fi
	@cd terraform && tfsec --no-colour --soft-fail
	@echo "✅ TFSec scan completed"

# =======================
# Deployment
# =======================

## Deploy to development environment
.PHONY: deploy-dev
deploy-dev:
	@echo "Deploying to development environment..."
	@$(MAKE) TF_ENV=dev tf-apply

## Deploy to staging environment
.PHONY: deploy-staging
deploy-staging:
	@echo "Deploying to staging environment..."
	@$(MAKE) TF_ENV=staging tf-apply

## Deploy to production environment
.PHONY: deploy-prod
deploy-prod:
	@echo "Deploying to production environment..."
	@$(MAKE) TF_ENV=prod tf-apply

# =======================
# Utilities
# =======================

## Clean up build artifacts and temporary files
.PHONY: clean
clean: docker-clean
	find . -type d -name "__pycache__" -exec rm -r {} +
	find . -type f -name "*.py[co]" -delete
	find . -type d -name ".pytest_cache" -exec rm -r {} +
	rm -rf .coverage htmlcov/

# =======================
# Aliases for backward compatibility
# =======================
.PHONY: build stop logs restart run-local rebuild-logs
build: docker-build
stop: docker-stop
logs: docker-logs
restart: docker-stop docker-run
run-local: run
rebuild-logs: docker-rebuild docker-logs

# Security
# ========

## Run Snyk security scan with high severity threshold
.PHONY: snyk-scan
snyk-scan:
	snyk test --severity-threshold=high

## Update dependencies to latest versions
.PHONY: update-deps
update-deps:
	pip list --outdated --format=columns | awk '{print $1}' | tail -n +3 | xargs -n1 pip install --upgrade

## Check for security vulnerabilities in dependencies (medium severity)
.PHONY: check-vulns
check-vulns:
	snyk test --severity-threshold=medium

## Monitor project for security vulnerabilities
.PHONY: monitor
monitor:
# ======================
# Dependencies Management
# ======================
# Install pip-tools if not already installed
PIP_TOOLS := $(shell pip show pip-tools >/dev/null 2>&1 || echo "pip-tools not installed")

# Update all requirements files
.PHONY: requirements
requirements: check-pip-tools
	@echo "Updating all requirements files..."
	@./scripts/update_requirements.sh

# Install development environment
.PHONY: dev-setuppip-sync requirements/requirements.txt requirements/dev-requirements.txt
dev-setup: check-pip-tools
	@echo "Setting up development environment..."
	pip install -r requirements/requirements.txt -r requirements/dev-requirements.txt

# Install production dependencies
.PHONY: prod-setup
prod-setup: check-pip-tools
	@echo "Setting up production environment..."
	pip install -r requirements/requirements.txt -r requirements/prod-requirements.txt

# Check for security vulnerabilities
.PHONY: security-check
security-check: check-pip-tools
	@echo "Checking for security vulnerabilities..."
	pip install -r requirements/security-requirements.txt
	safety check
	bandit -r app/

# Update a single requirements file
%.txt: %.in
	@echo "Updating $@..."
	pip-compile --upgrade -o $@ $<

# Check if pip-tools is installed
.PHONY: check-pip-tools
check-pip-tools:
	@if [ "$(PIP_TOOLS)" = "pip-tools not installed" ]; then \
		echo "Installing pip-tools..."; \
		pip install pip-tools; \
	fi

# Add a new package to base requirements
.PHONY: add-base-req
add-base-req:
	@if [ -z "$(PACKAGE)" ]; then \
		echo "Error: PACKAGE not specified. Usage: make add-base-req PACKAGE=package[==version]"; \
		exit 1; \
	fi
	@echo "$(PACKAGE)" >> requirements/base.in
	@echo "Added $(PACKAGE) to requirements/base.in"
	@$(MAKE) requirements

# Add a new development package
.PHONY: add-dev-req
add-dev-req:
	@if [ -z "$(PACKAGE)" ]; then \
		echo "Error: PACKAGE not specified. Usage: make add-dev-req PACKAGE=package[==version]"; \
		exit 1; \
	fi
	@echo "$(PACKAGE)" >> requirements/dev.in
	@echo "Added $(PACKAGE) to requirements/dev.in"
	@$(MAKE) requirements

# List all installed packages
.PHONY: list-reqs
list-reqs:
	pip list

# Show dependency tree
.PHONY: show-deps
show-deps:
	pipdeptree

# Check for dependency conflicts
.PHONY: check-reqs
check-reqs:
	pip check
	snyk monitor

# ======================
# GitHub Actions Setup
# ======================
.PHONY: setup-github-actions
setup-github-actions:
	aws cloudformation deploy \
	  --template-file cloudformation/github-actions-role.yml \
	  --stack-name github-actions-role \
	  --capabilities CAPABILITY_NAMED_IAM \
	  --parameter-overrides GitHubOrg=$(GITHUB_ORG) RepositoryName=$(REPO_NAME)
