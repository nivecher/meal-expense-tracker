# Terraform Configuration for Meal Expense Tracker

This directory contains the Terraform configuration for deploying the Meal Expense Tracker application to AWS.

## Backend Configuration

This project uses an S3 backend with DynamoDB for state locking. Follow the [backend setup
instructions](./backend/README.md) to configure the remote backend before initializing Terraform.

## Directory Structure

```Shell
terraform/
├── main.tf              # Root module with module calls
├── variables.tf         # Root variables
├── outputs.tf           # Root outputs
├── versions.tf          # Required providers and versions
├── providers.tf         # Provider configurations
├── locals.tf            # Common values and naming
├── terraform.tfvars     # Variable values (not versioned)
├── package_lambda.sh    # Script to package Lambda function
└── modules/             # Reusable modules
├── iam/             # IAM roles and policies
├── lambda/          # Lambda function
├── api_gateway/     # API Gateway
├── cloudfront/      # CloudFront distribution
├── s3/              # S3 buckets
└── ecr/             # ECR repository
```

## Prerequisites

- Terraform >= 1.2.0
- AWS CLI configured with appropriate credentials
- Python 3.13 (for Lambda runtime)

## Getting Started

1. **Initialize Terraform**

```bash

terraform init

```

1. **Review the execution plan**

```bash

terraform plan

```

1. **Apply the configuration**

```bash

terraform apply

```

1. **Package and deploy the Lambda function**

```bash

chmod +x package_lambda.sh
./package_lambda.sh

```

## Variables

Create a `terraform.tfvars` file with the following variables (see `terraform.tfvars.example` for reference):

```hcl

app_name    = "meal-expense-tracker"
environment = "dev"
aws_region = "us-east-1"

```

## Outputs

After applying the configuration, Terraform will output the following:

- API Gateway endpoint URL
- Lambda function name and ARN
- CloudFront distribution URL
- S3 bucket names (receipts and static files)
- Database connection string (stored in AWS Secrets Manager for Supabase)

## Cleaning Up

To destroy all resources created by this configuration:

```bash

terraform destroy

```

## Module Dependencies

The infrastructure has specific dependency relationships to avoid circular dependencies. See [DEPENDENCY_ORDER.md](./DEPENDENCY_ORDER.md) for detailed information about:

- Resource creation order
- Lambda ↔ API Gateway dependency management
- How circular dependencies are avoided
- Troubleshooting dependency issues

## Notes

- The Lambda function uses container images stored in ECR
- Database connection string is stored in AWS Secrets Manager (Supabase external PostgreSQL)
- All resources are tagged with the application name and environment
- Lambda is deployed without VPC for cost efficiency (connects to Supabase via HTTPS)
- **Important**: Lambda and API Gateway have a managed dependency to avoid circular references - see DEPENDENCY_ORDER.md
