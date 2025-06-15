# Terraform Configuration for Meal Expense Tracker

This directory contains the Terraform configuration for deploying the Meal Expense Tracker application to AWS.

## Backend Configuration

This project uses an S3 backend with DynamoDB for state locking. Follow the [backend setup instructions](./backend/README.md) to configure the remote backend before initializing Terraform.

## Directory Structure

```
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
    ├── network/         # VPC, subnets, routing
    ├── iam/             # IAM roles and policies
    ├── rds/             # Database resources
    ├── lambda/          # Lambda function
    └── api_gateway/     # API Gateway
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

2. **Review the execution plan**
   ```bash
   terraform plan
   ```

3. **Apply the configuration**
   ```bash
   terraform apply
   ```

4. **Package and deploy the Lambda function**
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
- RDS endpoint and credentials (stored in AWS Secrets Manager)
- VPC and subnet information

## Cleaning Up

To destroy all resources created by this configuration:

```bash
terraform destroy
```

## Notes

- The Lambda function code is expected to be in the `lambda/` directory
- Database credentials are stored in AWS Secrets Manager
- All resources are tagged with the application name and environment
