# Environment Configuration

This directory contains the configuration for different deployment environments (dev, staging, prod).

## Directory Structure

```
environments/
├── dev/
│   ├── backend.hcl        # Backend configuration for dev
│   └── terraform.tfvars   # Variable overrides for dev
├── staging/               # Same structure as dev
└── prod/                  # Same structure as dev

```

## Environment Variables

Each environment has its own `terraform.tfvars` file with environment-specific settings. Common variables include:

- `environment`: The environment name (dev/staging/prod)
- `aws_region`: The AWS region to deploy to
- `app_name`: The application name
- `base_domain`: Base domain name (default: `nivecher.com`)
- `app_subdomain`: App subdomain (default: `meals`)
- `api_domain_prefix`: API subdomain prefix (default: `api`)
- `lambda_architecture`: Lambda architecture (`x86_64` or `arm64`)
- `lambda_memory_size`: Lambda memory in MB
- `lambda_timeout`: Lambda timeout in seconds
- `lambda_reserved_concurrency`: Reserved concurrency for Lambda
- `run_migrations`: Whether to run DB migrations on first deployment
- `log_level`: Application log level
- `monthly_budget_amount`: Monthly budget in USD

## Usage

1. Navigate to the environment directory:

```bash

cd terraform/environments/dev  # or staging/prod

```

1. Initialize Terraform with the backend configuration:

```bash

terraform init -backend-config=backend.hcl

```

1. Review the planned changes:

```bash

terraform plan

```

1. Apply the changes:

```bash

terraform apply

```

## Adding a New Environment

1. Create a new directory for the environment:

```bash

mkdir -p terraform/environments/new-env

```

1. Copy the backend configuration:

```bash

cp terraform/environments/dev/backend.hcl terraform/environments/new-env/

```

Update the `key` in `backend.hcl` to use a unique path.

1. Create a new `terraform.tfvars` file with appropriate settings.

1. Create a `main.tf` that references the common configuration and any environment-specific resources.

## Best Practices

- Never commit sensitive values to version control
- Use remote state locking with DynamoDB
- Enable versioning on the S3 bucket
- Use environment-specific IAM roles and policies
- Regularly back up your Terraform state
