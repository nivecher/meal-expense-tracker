# Setup Scripts

This directory contains utility scripts for setting up and managing the meal expense tracker application.

## Google Places API Key Setup

To set up the Google Places API key in AWS Secrets Manager, use the `setup_google_places_secret.py` script.

### Prerequisites

- Python 3.6 or higher
- AWS CLI configured with appropriate credentials
- `boto3` Python package installed (`pip install boto3`)

### Usage

```bash
# Basic usage
./scripts/setup_google_places_secret.py --api-key "YOUR_GOOGLE_PLACES_API_KEY"

# With custom AWS profile and region
./scripts/setup_google_places_secret.py \
  --api-key "YOUR_GOOGLE_PLACES_API_KEY" \
  --profile your-aws-profile \
  --region us-east-1 \
  --app-name meal-expense-tracker \
  --environment dev
```

### Options

- `--api-key`: (Required) Your Google Places API key
- `--profile`: (Optional) AWS profile to use (defaults to default profile)
- `--region`: (Optional) AWS region (defaults to us-east-1)
- `--app-name`: (Optional) Application name (defaults to 'meal-expense-tracker')
- `--environment`: (Optional) Deployment environment: dev, staging, or prod (defaults to 'dev')

### What the Script Does

1. Creates or updates a secret in AWS Secrets Manager with the name format: `{app_name}/{environment}/google-places-api-key`
2. Stores the Google Places API key as the secret value
3. Tags the secret with appropriate metadata
4. Outputs the secret ARN that you need to add to your Terraform configuration

### Terraform Configuration

After running the script, update your Terraform configuration with the secret ARN:

```hcl
# In your environment's variables file (e.g., dev.tfvars)
google_places_api_key_secret_arn = "arn:aws:secretsmanager:region:account-id:secret:your-secret-name-xxxxxx"
```

### Security Notes

- The script requires IAM permissions to create/update secrets in AWS Secrets Manager
- The secret is encrypted using AWS KMS
- The secret is tagged with the environment and application name for better resource management
- Never commit actual API keys to version control
