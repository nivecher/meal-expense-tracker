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

# Build the Docker image
build:
	docker build -t $(IMAGE_NAME) .

# Run the container with .env file
run:
	docker run -d -p $(PORT):$(PORT) -v $(VOLUME_NAME):/app/instance --env-file .env --name $(CONTAINER_NAME) $(IMAGE_NAME)

# Run the application locally using Python
run-local:
	PYTHONPATH=. FLASK_APP=wsgi.py FLASK_ENV=development flask run --port $(PORT)

# Stop and remove the container
stop:
	docker rm -f $(CONTAINER_NAME)

# Show container logs
logs:
	docker logs -f $(CONTAINER_NAME)

# Clean up containers and volumes
clean:
	docker rm -f $(CONTAINER_NAME) || true
	docker volume rm $(VOLUME_NAME) || true

# Rebuild and run with .env file
rebuild: stop build run

# Rebuild, run and follow logs
rebuild-logs: rebuild logs

# Quick restart (stop and run)
restart: stop run

# Quick restart with logs
restart-logs: restart logs

test:
	PYTHONPATH=. pytest tests/

lint:
	black .
	flake8 .

lint-infra:
	cd terraform && terraform fmt

check-infra:
	cd terraform && terraform fmt -check
	cd terraform && terraform init -backend=false
	cd terraform && terraform validate
	checkov -d terraform --quiet
	# checkov -d cloudformation --quiet

load-test:
	python3 -m locust -f tests/load/locustfile.py --headless -u 10 -r 2 -t 30s --host=http://localhost:5000

setup-github-actions:
	aws cloudformation deploy \
	  --template-file cloudformation/github-actions-role.yml \
	  --stack-name github-actions-role \
	  --capabilities CAPABILITY_NAMED_IAM \
	  --parameter-overrides GitHubOrg=$(GITHUB_ORG) RepositoryName=$(REPO_NAME)
