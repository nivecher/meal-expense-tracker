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

# Terraform settings
ENV ?= dev
TF_ENV ?= $(ENV)
TF_CMD = cd terraform && make ENV=$(TF_ENV)
TF_PARALLELISM ?= 30
TF_ARGS ?= -parallelism=$(TF_PARALLELISM) -refresh=true

# GitHub settings
GITHUB_ORG ?= nivecher
REPO_NAME ?= meal-expense-tracker

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
	@echo "  \033[1mmake setup-tf-backend\033[0m  Provision remote backend & generate configs"
	@echo "  \033[1mmake destroy-tf-backend [STACK=terraform-backend REGION=us-east-1]\033[0m  Delete backend resources"

	@echo "\n\033[1;34mDeployment:\033[0m"
	@echo "  \033[1mmake deploy-dev\033[0m      Deploy to development environment"
	@echo "  \033[1mmake deploy-staging\033[0m  Deploy to staging environment"
	@echo "  \033[1mmake deploy-prod\033[0m     Deploy to production environment"
	@echo "  \033[1mmake package-lambda\033[0m  Create Lambda deployment package using package_lambda.sh"
	@echo "  \033[1mmake update-lambda\033[0m   Update Lambda function code with latest package"
	@echo "  \033[1mmake invoke-lambda\033[0m   Invoke Lambda function with test event"

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
	@echo "\n\033[1m=== Setting up development environment ===\033[0m"
	@./scripts/setup-local-dev.sh

## Run the application locally
.PHONY: run
run:
	FLASK_APP=$(FLASK_APP) FLASK_ENV=$(FLASK_ENV) flask run --port $(PORT)

## Run linters
.PHONY: lint
lint:
	@echo "\n\033[1m=== Running Python Linters ===\033[0m"
	@flake8 app/ tests/
	@black --check app/ tests/ migrations/ */*.py *.py
	@echo "\n\033[1m=== Running Shell Script Linter ===\033[0m"
	@find . -type f -name '*.sh' \
		-not -path '*/.*' \
		-not -path '*/venv/*' \
		-not -path '*/Python-*/*' \
		-print0 | xargs -0 -I{} sh -c 'echo "Checking {}" && shellcheck -x {}' || true

## Format code
.PHONY: format
format: format-python format-shell

## Format Python code
.PHONY: format-python
format-python:
	@echo "\n\033[1m=== Formatting Python code ===\033[0m"
	@black app/ tests/ migrations/ */*.py *.py
	@autoflake --in-place --remove-all-unused-imports --recursive app/ tests/

## Format Shell scripts
.PHONY: format-shell
format-shell:
	@if command -v shfmt >/dev/null 2>&1; then \
		echo "\n\033[1m=== Formatting Shell scripts ===\033[0m"; \
		find . -type f -name '*.sh' \
			-not -path '*/.*' \
			-not -path '*/venv/*' \
			-not -path '*/Python-*/*' \
			-print0 | xargs -0 -I{} sh -c 'echo "Formatting {}" && shfmt -i 2 -w "{}"'; \
	else \
		echo "\n\033[1;33m⚠️ shfmt is not installed. Shell scripts will not be formatted.\033[0m"; \
		echo "To enable shell script formatting, please install shfmt:"; \
		echo "  - Using Go: go install mvdan.cc/sh/v3/cmd/shfmt@latest"; \
		echo "  - Or download from: https://github.com/mvdan/sh/releases"; \
		echo "  - Or via package manager: brew install shfmt / apt-get install shfmt / etc."; \
		echo "\nContinuing with Python formatting only...\n"; \
	fi

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

# ---------------------------
# Terraform backend helper
# ---------------------------
# Ensures backend.hcl exists for the specified environment.
# If missing, instructs user to run setup-tf-backend.
# ---------------------------
tffile = terraform/environments/$(TF_ENV)/backend.hcl

## Initialize Terraform for a specific environment
.PHONY: tf-init
tf-init:
	@if [ -z "$(TF_ENV)" ]; then \
		echo "Error: TF_ENV is not set. Usage: make tf-init TF_ENV=<env>"; \
		exit 1; \
	fi
	@if [ ! -f "terraform/environments/$(TF_ENV)/backend.tf" ]; then \
		echo "Error: backend.tf not found for environment $(TF_ENV)."; \
		echo "Run 'make setup-tf-backend' first to generate backend configurations."; \
		exit 1; \
	fi
	@echo "🚀 Initializing Terraform with parallelism=$(TF_PARALLELISM) in $(TF_ENV) environment..."
	@cd terraform/environments/$(TF_ENV) && \
	TF_PLUGIN_CACHE_DIR="$(HOME)/.terraform.d/plugin-cache" \
	TF_IN_AUTOMATION=1 \
	terraform init -input=false -backend=true -get=true -upgrade $(TF_ARGS) && terraform init -backend-config=backend.hcl

## Generate a plan without applying
.PHONY: tf-plan
tf-plan: tf-init
	@echo "Creating Terraform plan for environment: $(TF_ENV)"
	@if [ ! -f "terraform/environments/$(TF_ENV)/terraform.tfvars" ]; then \
		echo "Error: terraform/environments/$(TF_ENV)/terraform.tfvars not found."; \
		echo "Please create the file with the required variables for the $(TF_ENV) environment."; \
		exit 1; \
	fi
	@cd terraform/environments/$(TF_ENV) && terraform plan \
		-var-file=terraform.tfvars \
		-out=tfplan-$(TF_ENV) \
		-var="environment=$(TF_ENV)"

## Apply the most recent plan
.PHONY: tf-apply
tf-apply:
	@echo "Applying Terraform changes to environment: $(TF_ENV)"
	@cd terraform/environments/$(TF_ENV) && terraform apply tfplan-$(TF_ENV)

## Destroy all resources in the environment
.PHONY: tf-destroy
tf-destroy:
	@echo "WARNING: This will destroy all resources in the $(TF_ENV) environment!"
	@read -p "Are you sure you want to continue? [y/N] " confirm && \
		[ $$confirm = y ] || [ $$confirm = Y ] || (echo "Aborting..."; exit 1)
	@cd terraform/environments/$(TF_ENV) && terraform destroy \
		-var-file=terraform.tfvars \
		-var="environment=$(TF_ENV)"

## Validate Terraform configuration
.PHONY: tf-validate
tf-validate:
	@echo "Validating Terraform configuration..."
	@cd terraform/environments/$(TF_ENV) && terraform init -backend=false
	@cd terraform/environments/$(TF_ENV) && terraform validate

## Format Terraform files
.PHONY: tf-fmt
tf-fmt:
	@cd terraform/environments/$(TF_ENV) && terraform fmt -recursive

## Clean Terraform lock files and cache
.PHONY: tf-clean
tf-clean:
	@echo "Cleaning Terraform lock files and cache..."
	@rm -rf terraform/environments/$(TF_ENV)/.terraform terraform/environments/$(TF_ENV)/.terraform.lock.hcl
	@echo "Terraform cache and lock files have been removed"

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
	@cd terraform/environments/$(TF_ENV) && trivy config --tf-vars terraform.tfvars .
	@echo "\n📋 Scanning CloudFormation files..."
	@find . -path "*/cloudformation/*.y*ml" -type f -exec echo "Scanning {}" \; -exec trivy config "{}" \;
	@echo "✅ Trivy scan completed"

# -------------------------------------------------------
# Provision or update the remote backend (S3 & DynamoDB)
# Usage: make setup-tf-backend [ARGS=...]
# Any flags in ARGS will be forwarded to the shell script.
# -------------------------------------------------------
setup-tf-backend:
	@echo "Setting up Terraform backend via CloudFormation..."
	@./scripts/setup-terraform-backend.sh $(ARGS)

DESTROY_STACK ?= terraform-backend
DESTROY_REGION ?= us-east-1

# -------------------------------------------------------
# Set default values for stack name and region
DEFAULT_STACK_NAME ?= terraform-backend
DEFAULT_REGION ?= us-east-1

# Delete the CloudFormation stack that hosts the Terraform backend
# Usage: make destroy-tf-backend [DESTROY_STACK=name] [DESTROY_REGION=region]
# Default: DESTROY_STACK=terraform-backend, DESTROY_REGION=us-east-1
# -------------------------------------------------------
destroy-tf-backend:
	@STACK_NAME="$(or $(DESTROY_STACK),$(DEFAULT_STACK_NAME))"; \
	REGION="$(or $(DESTROY_REGION),$(DEFAULT_REGION))"; \
	echo "Deleting Terraform backend stack '$$STACK_NAME' in region '$$REGION'..."; \
	aws cloudformation delete-stack --stack-name "$$STACK_NAME" --region "$$REGION"; \
	aws cloudformation wait stack-delete-complete --stack-name "$$STACK_NAME" --region "$$REGION" || true; \
	echo "✅ Terraform backend stack '$$STACK_NAME' deletion completed in region '$$REGION'."

# =======================
# Deployment
# =======================

## Deploy to development environment
.PHONY: deploy-dev
deploy-dev:
	@echo "Deploying to development environment..."
	@$(MAKE) TF_ENV=dev tf-init
	@$(MAKE) TF_ENV=dev tf-plan
	@$(MAKE) TF_ENV=dev tf-apply

## Deploy to staging environment
.PHONY: deploy-staging
deploy-staging:
	@echo "Deploying to staging environment..."
	@echo "Are you sure you want to deploy to staging? This will apply all pending changes."
	@read -p "Type 'yes' to continue: " confirm && [ $$confirm = yes ]
	@$(MAKE) TF_ENV=staging tf-init
	@$(MAKE) TF_ENV=staging tf-plan
	@$(MAKE) TF_ENV=staging tf-apply

## Deploy to production environment
.PHONY: deploy-prod
deploy-prod:
	@echo "WARNING: You are about to deploy to PRODUCTION!"
	@echo "This will apply all pending changes to your production environment."
	@read -p "Type 'production' to continue: " confirm && [ "$$confirm" = "production" ]
	@$(MAKE) TF_ENV=prod tf-init
	@$(MAKE) TF_ENV=prod tf-plan
	@$(MAKE) TF_ENV=prod tf-apply

# =======================
# Lambda Deployment
# =======================

## Package the application for Lambda deployment
.PHONY: package-lambda
package-lambda:
	@echo "\033[1m📦 Creating Lambda deployment package...\033[0m"
	@if [ ! -x "$(shell which zip)" ]; then \
		echo "Error: 'zip' command is required but not installed."; \
		exit 1; \
	fi
	@if [ ! -x "$(shell which pip)" ]; then \
		echo "Error: 'pip' command is required but not installed."; \
		exit 1; \
	fi
	@chmod +x scripts/package-lambda.sh
	@# Ignore the exit code from the script as zip might return non-zero on success
	@if ! scripts/package-lambda.sh; then \
		echo "\033[1;33m⚠️  Package script completed with warnings, but continuing...\033[0m"; \
	fi

## Update the Lambda function with the latest package
.PHONY: update-lambda
update-lambda: package-lambda
	@echo "\033[1m🔄 Updating Lambda function...\033[0m"
	@if [ -z "$(LAMBDA_FUNCTION_NAME)" ]; then \
		echo "Error: LAMBDA_FUNCTION_NAME is not set."; \
		echo "Please set LAMBDA_FUNCTION_NAME environment variable or run:"; \
		echo "  make update-lambda LAMBDA_FUNCTION_NAME=your-function-name"; \
		echo "Or use Terraform output:"; \
		echo "  make update-lambda LAMBDA_FUNCTION_NAME=\`cd terraform && terraform output -raw lambda_function_name\`"; \
		exit 1; \
	fi
	@aws lambda update-function-code \
		--function-name "$(LAMBDA_FUNCTION_NAME)" \
		--zip-file "fileb://dist/app.zip" \
		--publish \
		--output json

## Invoke the Lambda function with a test event
.PHONY: invoke-lambda
	@echo "\033[1m🚀 Invoking Lambda function...\033[0m"
	@if [ -z "$(LAMBDA_FUNCTION_NAME)" ]; then \
		echo "Error: LAMBDA_FUNCTION_NAME is not set."; \
		echo "Please set LAMBDA_FUNCTION_NAME environment variable or run:"; \
		echo "  make invoke-lambda LAMBDA_FUNCTION_NAME=your-function-name"; \
		echo "Or use Terraform output:"; \
		echo "  make invoke-lambda LAMBDA_FUNCTION_NAME=\`cd terraform && terraform output -raw lambda_function_name\`"; \
		exit 1; \
	fi
	@mkdir -p tmp
	@echo '{"version":"2.0","routeKey":"GET /api/health","rawPath":"/api/health","requestContext":{"http":{"method":"GET","path":"/api/health"},"requestId":"test-invoke-request"},"isBase64Encoded":false}' > tmp/test-event.json
	@aws lambda invoke \
		--function-name "$(LAMBDA_FUNCTION_NAME)" \
		--payload file://tmp/test-event.json \
		--cli-binary-format raw-in-base64-out \
		--log-type Tail \
		--output json \
		--query 'LogResult' \
		tmp/response.json | base64 --decode
	@echo "\n\033[1m📄 Response:\033[0m"
	@cat tmp/response.json | jq .

# =======================
# GitHub Actions
# =======================

# Setup GitHub Actions workflows
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
