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
FLASK_APP = wsgi:app
FLASK_ENV = development

# Enable BuildKit for better build performance and features
export DOCKER_BUILDKIT=1
export PYTHONPATH

# =======================
# Virtual Environment
# =======================

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
	@echo "  \033[1mmake deploy-lambda\033[0m   Deploy the Lambda function with the latest package"

	@echo "\n\033[1;34mVirtual Environment:\033[0m"
	@echo "  \033[1mmake venv\033[0m           Create Python virtual environment (if not exists)"

	@echo "\n\033[1;34mDocker (Container Runtime):\033[0m"
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
.PHONY: lint lint-all lint-python lint-html lint-js lint-css

## Run all linters
lint: lint-python lint-html lint-js lint-css

## Run all linters including optional ones
lint-all: lint lint-optional

## Python linter
lint-python:
	@echo "\n\033[1m=== Running Python Linter ===\033[0m"
	@flake8 app tests
	@black --check app tests

## HTML template linter
lint-html:
	@echo "\n\033[1m=== Running HTML Template Linter ===\033[0m"
	@djlint app/templates --profile=django --lint

## JavaScript linter (if you add JavaScript files later)
.PHONY: lint-js
lint-js:
	@if [ -d "app/static/js" ]; then \
		echo "\n\033[1m=== Running JavaScript Linter ===\033[0m"; \
		npx eslint app/static/js --ext .js; \
	fi

## CSS linter
.PHONY: lint-css
lint-css:
	@if [ -d "app/static/css" ]; then \
		echo "\n\033[1m=== Running CSS Linter ===\033[0m"; \
		npx stylelint "app/static/css/**/*.css"; \
	fi

## Optional linters (not run by default)
.PHONY: lint-optional
lint-optional: lint-security lint-docker

## Security linter
.PHONY: lint-security
lint-security:
	@echo "\n\033[1m=== Running Security Linter ===\033[0m"
	@pip-audit || echo "pip-audit not installed, skipping security audit"

format-html:
	@echo "\n\033[1m=== Formatting HTML Templates ===\033[0m"
	@djlint app/templates --profile=django --reformat

format: format-html
	@echo "\n\033[1m=== Running Shell Script Linter ===\033[0m"
	@find . -type f -name '*.sh' \
		-not -path '*/.*' \
		-not -path '*/venv/*' \
		-not -path '*/Python-*/*' \
		-print0 | xargs -0 -I{} sh -c 'echo "Checking {}" && shellcheck -x {}' || true

## Format code
.PHONY: format
format: format-html format-python format-shell

## Format Python code
.PHONY: format-python
format-python:
	@echo "\n\033[1m=== Formatting Python code ===\033[0m"
	@isort app/ tests/ migrations/ *.py
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
TF_ROOT := $(shell pwd)/terraform
TF_ENV_DIR = $(TF_ROOT)/environments/$(TF_ENV)
TF_BACKEND_CONFIG = $(TF_ENV_DIR)/backend.hcl

## Initialize Terraform for a specific environment
.PHONY: tf-init
tf-init:
	@echo "🚀 Initializing Terraform in $(TF_ENV) environment..."
	@cd terraform && \
	TF_PLUGIN_CACHE_DIR="$(HOME)/.terraform.d/plugin-cache" \
	TF_IN_AUTOMATION=1 \
	terraform init -reconfigure -backend-config=environments/$(TF_ENV)/backend.hcl

## Generate a plan without applying
.PHONY: tf-plan
tf-plan: tf-init
	@echo "Creating Terraform plan for environment: $(TF_ENV)"
	@if [ ! -f "terraform/environments/$(TF_ENV)/terraform.tfvars" ]; then \
		echo "Error: terraform.tfvars not found in terraform/environments/$(TF_ENV)/"; \
		echo "Please create the file with the required variables for the $(TF_ENV) environment."; \
		exit 1; \
	fi
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
tf-apply:
	@if [ ! -f "terraform/environments/$(TF_ENV)/tfplan-$(TF_ENV)" ]; then \
		echo "Error: No Terraform plan found. Run 'make tf-plan' first."; \
		exit 1; \
	fi
	@echo "Applying Terraform changes to environment: $(TF_ENV)"
	@cd terraform && \
	terraform apply \
		-input=false \
		-lock=true \
		-parallelism=$(TF_PARALLELISM) \
		environments/$(TF_ENV)/tfplan-$(TF_ENV)

## Destroy all resources in the environment
.PHONY: tf-destroy
tf-destroy:
	@echo "WARNING: This will destroy all resources in the $(TF_ENV) environment!"
	@read -p "Are you sure you want to continue? [y/N] " confirm && \
		[ $$confirm = y ] || [ $$confirm = Y ] || (echo "Aborting..."; exit 1)
	@cd terraform && \
	terraform destroy \
		-var-file=environments/$(TF_ENV)/terraform.tfvars \
		-var="environment=$(TF_ENV)" \
		-input=false \
		-lock=true \
		-parallelism=$(TF_PARALLELISM) \
		-auto-approve

## Validate Terraform configuration
.PHONY: tf-validate
tf-validate:
	@echo "Validating Terraform configuration for $(TF_ENV)..."
	@cd terraform && \
	terraform validate

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

## Deploy to dev environment
.PHONY: deploy-dev
deploy-dev: check-lambda-package
	@echo "Deploying to dev environment..."
	@./scripts/deploy_lambda.sh \
	  --function-name "$(LAMBDA_FUNCTION_NAME)-dev" \
	  --environment dev \
	  --profile "$(DEFAULT_AWS_PROFILE)" \
	  --region "$(DEFAULT_AWS_REGION)" \
	  --package both

## Deploy to staging environment
.PHONY: deploy-staging
deploy-staging: check-lambda-package
	@echo "Deploying to staging environment..."
	@read -p "This will deploy to the staging environment. Continue? [y/N] " confirm && [ "$$confirm" = "y" ] || [ "$$confirm" = "Y" ] || (echo "Aborting..."; exit 1)
	@./scripts/deploy_lambda.sh \
	  --function-name "$(LAMBDA_FUNCTION_NAME)-staging" \
	  --environment staging \
	  --profile "$(DEFAULT_AWS_PROFILE)" \
	  --region "$(DEFAULT_AWS_REGION)" \
	  --package both

## Deploy to production environment
.PHONY: deploy-prod
deploy-prod: check-lambda-package
	@echo "WARNING: You are about to deploy to PRODUCTION!"
	@echo "This will apply all pending changes to your production environment."
	@read -p "Type 'production' to continue: " confirm && [ "$$confirm" = "production" ]
	@./scripts/deploy_lambda.sh \
	  --function-name "$(LAMBDA_FUNCTION_NAME)" \
	  --environment prod \
	  --profile "$(DEFAULT_AWS_PROFILE)" \
	  --region "$(DEFAULT_AWS_REGION)" \
	  --package both

# =======================
# Lambda Deployment
# =======================

## Deploy the latest Lambda function code
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

## Package the application and dependencies for Lambda deployment
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

## Run database migrations on the deployed Lambda function
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

## Package only the Lambda layer
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
	@echo "\033[1;32m✅ Lambda layer package created at dist/layers/python-dependencies.zip\033[0m"

.PHONY: deploy
## Deploy the Lambda function and run migrations
deploy:
	@echo "🚀 Deploying Lambda function and running migrations..."
	@read -p "Enter Lambda function name: " FUNCTION_NAME; \
	read -p "Enter AWS region [$(DEFAULT_AWS_REGION)]: " REGION; \
	read -p "Enter AWS profile [$(DEFAULT_AWS_PROFILE)]: " PROFILE; \
	read -p "Enter environment [dev]: " ENV; \
	REGION=$${REGION:-$(DEFAULT_AWS_REGION)}; \
	PROFILE=$${PROFILE:-$(DEFAULT_AWS_PROFILE)}; \
	ENV=$${ENV:-dev}; \
	echo "🚀 Deploying Lambda function $$FUNCTION_NAME in region $$REGION with profile $$PROFILE (env: $$ENV)..."; \
	./scripts/deploy_lambda.sh \
	  --function-name "$$FUNCTION_NAME" \
	  --region "$$REGION" \
	  --profile "$$PROFILE" \
	  --environment "$$ENV" \
	  --package both

## Check if Lambda package exists
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

.PHONY: run-migrations-local
run-migrations-local: test-db-connection
	@echo "\033[1m🔄 Running database migrations...\033[0m"
	@if ! python3 scripts/test_db_connection.py --migrate; then \
		echo "\033[1;31m❌ Database migrations failed\033[0m"; \
		exit 1; \
	fi
	@echo "\033[1;32m✅ Database migrations completed successfully!\033[0m"

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

## Deploy the Lambda function with the latest package
# Default Lambda function name
LAMBDA_FUNCTION_NAME ?= meal-expense-tracker-$(TF_ENV)

## Invoke the Lambda function with a test event
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

# Default requirements files
REQUIREMENTS_FILES = requirements.txt requirements-dev.txt requirements-prod.txt

# Generate requirements files if they don't exist
.PHONY: check-requirements
check-requirements:
	@for req in $(REQUIREMENTS_FILES); do \
		if [ ! -f "$$req" ]; then \
			echo "$$req not found, generating..."; \
			$(MAKE) $$req; \
		fi; \
	done

# Update all requirements files
.PHONY: requirements
requirements: check-pip-tools
	@echo "Updating requirements files..."
	@scripts/update_requirements.sh

# Install development environment
.PHONY: dev-setup
dev-setup: check-pip-tools requirements
	@echo "Setting up development environment..."
	pip install -r requirements.txt -r requirements-dev.txt

# Install production dependencies
.PHONY: prod-setup
prod-setup: check-pip-tools requirements
	@echo "Setting up production environment..."
	pip install -r requirements-prod.txt

# Check for security vulnerabilities
.PHONY: security-check
security-check: check-pip-tools
	@echo "Checking for security vulnerabilities..."
	pip install safety bandit
	safety check -r requirements.txt
	bandit -r app/

# Get absolute path to the project directory
PROJECT_DIR := $(shell pwd)

# Clean up generated requirements files
.PHONY: clean-requirements
clean-requirements:
	rm -f requirements.txt requirements-dev.txt requirements-prod.txt

# Update a single requirements file
%.txt: %.in
	@echo "Updating $@..."
	@# Create a temporary file in the same directory as the target to avoid cross-device links
	@TMP_FILE=$$(mktemp -p . .tmp_XXXXXXXXXX) && \
	trap 'rm -f "$$TMP_FILE"' EXIT && \
	pip-compile --upgrade -o "$$TMP_FILE" $< && \
	mv "$$TMP_FILE" $@ || { rm -f "$$TMP_FILE"; exit 1; }

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
