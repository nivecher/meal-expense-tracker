# Meal Expense Tracker Makefile
# =====================

.PHONY: build run test lint clean run-local

# Enable BuildKit for better build performance and features
export DOCKER_BUILDKIT=1

# Variables
CONTAINER_NAME = meal-expense-app
IMAGE_NAME = meal-expense-tracker
PORT = 5000
VOLUME_NAME = meal-expense-db
GITHUB_ORG = nivecher
REPO_NAME = meal-expense-tracker

# Docker Operations
# ================

## Build the Docker image
build:
	docker build -t $(IMAGE_NAME) .

## Run the container with .env file
run:
	docker run -d -p $(PORT):$(PORT) -v $(VOLUME_NAME):/app/instance --env-file .env --name $(CONTAINER_NAME) $(IMAGE_NAME)

## Run the application locally using Python
run-local:
	PYTHONPATH=. FLASK_APP=wsgi.py FLASK_ENV=development flask run --port $(PORT)

## Stop and remove the container
stop:
	docker rm -f $(CONTAINER_NAME)

## Show container logs
logs:
	docker logs -f $(CONTAINER_NAME)

## Clean up containers and volumes
clean:
	docker rm -f $(CONTAINER_NAME) || true
	docker volume rm $(VOLUME_NAME) || true

## Rebuild and run with .env file
rebuild: stop build run

## Rebuild, run and follow logs
rebuild-logs: rebuild logs

## Quick restart (stop and run)
restart: stop run

## Quick restart with logs
restart-logs: restart logs

# Development
# ==========

## Run tests
.PHONY: test
test:
	PYTHONPATH=. pytest tests/

## Run linters
.PHONY: lint
lint:
	black .
	flake8 .

## Run infrastructure linters
.PHONY: lint-infra
lint-infra:
	cd terraform && terraform fmt

## Check infrastructure
.PHONY: check-infra
check-infra:
	cd terraform && terraform fmt -check
	cd terraform && terraform init -backend=false
	cd terraform && terraform validate
	checkov -d terraform --quiet

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
	snyk monitor

# Requirements Management
# ======================

## Sync requirements.in with current environment
.PHONY: sync-reqs
sync-reqs:
	pip-sync requirements.txt

## Update requirements.in with latest compatible versions
.PHONY: update-reqs
update-reqs:
	pip-compile --upgrade requirements.in

## Rebuild requirements.txt from requirements.in
.PHONY: rebuild-reqs
rebuild-reqs:
	pip-compile requirements.in

## Add a new dependency to requirements.in and rebuild
.PHONY: add-req
add-req:
	pip-compile --add-package $(PACKAGE) requirements.in

# Remove a dependency from requirements.in and rebuild
remove-req:
	pip-compile --remove-package $(PACKAGE) requirements.in

# List all dependencies
list-reqs:
	pip list --format=columns

# Show dependency tree
show-deps:
	pipdeptree

# Check for conflicts in requirements
check-reqs:
	pip check

## Run load tests
.PHONY: load-test
load-test:
	python3 -m locust -f tests/load/locustfile.py --headless -u 10 -r 2 -t 30s --host=http://localhost:5000

setup-github-actions:
	aws cloudformation deploy \
	  --template-file cloudformation/github-actions-role.yml \
	  --stack-name github-actions-role \
	  --capabilities CAPABILITY_NAMED_IAM \
	  --parameter-overrides GitHubOrg=$(GITHUB_ORG) RepositoryName=$(REPO_NAME)
