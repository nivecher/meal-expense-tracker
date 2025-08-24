# Environment Configuration

This directory contains the configuration for different deployment environments (dev, staging, prod).

## Directory Structure

```
environments/
├── dev/
│   ├── backend.hcl        # Backend configuration for dev
│   ├── main.tf            # Main configuration for dev
│   └── terraform.tfvars   # Variable overrides for dev
├── staging/               # Same structure as dev
└── prod/                  # Same structure as dev

```

## Environment Variables

Each environment has its own `terraform.tfvars` file with environment-specific settings. Common variables include:

- `environment`: The environment name (dev/staging/prod)
- `aws_region`: The AWS region to deploy to
- `app_name`: The application name
- `instance_type`: EC2 instance type
- `db_instance_class`: RDS instance class
- `db_allocated_storage`: RDS storage in GB
- `min_size`/`max_size`/`desired_size`: Auto-scaling group sizes
- `enable_xray_tracing`: Enable AWS X-Ray tracing
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
