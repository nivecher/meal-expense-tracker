# Setup Scripts

This directory contains utility scripts for setting up and managing the meal expense tracker application.

## Google Maps API Key Setup

To set up the Google Maps API key in AWS Secrets Manager, use the `setup_google_maps_secret.py` script.

### Prerequisites

- Python 3.6 or higher
- AWS CLI configured with appropriate credentials
- `boto3` Python package installed (`pip install boto3`)

### Usage

```bash
## Basic usage
./scripts/setup_google_maps_secret.py --api-key "YOUR_GOOGLE_MAPS_API_KEY"

## With custom AWS profile and region
./scripts/setup_google_maps_secret.py \
  --api-key "YOUR_GOOGLE_MAPS_API_KEY" \
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

1. Creates or updates a secret in AWS Secrets Manager with the name format:
   `{app_name}/{environment}/google/maps-api-key`
2. Stores the Google Maps API key as the secret value
3. Tags the secret with appropriate metadata
4. Outputs the secret ARN that you need to add to your Terraform configuration

### Terraform Configuration

After running the script, update your Terraform configuration with the secret ARN:

```hcl

## In your environment's variables file (e.g., dev.tfvars)
google_maps_api_key_secret_arn = "arn:aws:secretsmanager:region:account-id:secret:your-secret-name-xxxxxx"

```

### Security Notes

- The script requires IAM permissions to create/update secrets in AWS Secrets Manager
- The secret is encrypted using AWS KMS
- The secret is tagged with the environment and application name for better resource management
- Never commit actual API keys to version control

## S3 MFA Delete Enablement

To enable MFA delete protection on S3 buckets, use the `enable_s3_mfa_delete.sh` script.
This adds an extra layer of security by requiring MFA authentication to permanently delete object versions or change the bucket's versioning state.

### MFA Delete Prerequisites

- AWS CLI installed and configured
- Terraform installed (optional, for automatic bucket name detection)
- Root account credentials with MFA device configured
- MFA device (hardware or virtual) activated for the root account

### MFA Delete Usage

```bash
# Basic usage (automatically detects bucket names from Terraform)
./scripts/enable_s3_mfa_delete.sh

# The script will:
# 1. Detect bucket names from Terraform outputs (if available)
# 2. Prompt for MFA code
# 3. Enable MFA delete on receipts bucket
# 4. Enable MFA delete on logs bucket (if it exists)
# 5. Verify the configuration
```

### MFA Delete Script Process

1. Checks prerequisites (AWS CLI, Terraform, credentials)
2. Gets AWS account ID automatically
3. Retrieves bucket names from Terraform outputs or prompts manually
4. Prompts for MFA code securely (input is hidden)
5. Enables MFA delete on both receipts and logs buckets
6. Verifies that MFA delete is enabled

### Important Notes

- **Root Account Required**: MFA delete can only be enabled using root account credentials
- **MFA Device Required**: You must have an MFA device configured for the root account
- **One-Time Operation**: After enabling, you'll need MFA to:
  - Permanently delete object versions
  - Change bucket versioning settings
  - Disable MFA delete (also requires MFA)
- **Terraform Limitation**: While Terraform can declare `mfa_delete = "Enabled"` in the configuration, AWS requires CLI to actually enable it

### Security Benefits

- Prevents accidental or malicious deletion of object versions
- Requires MFA authentication for critical bucket operations
- Adds an extra layer of protection for sensitive data
- Complies with security best practices and compliance requirements

### Troubleshooting

If the script fails:

1. **Check AWS Credentials**: Ensure you're using root account credentials
   ```bash
   aws sts get-caller-identity
   ```

2. **Verify MFA Device**: Ensure MFA is configured for the root account
   - Go to AWS IAM Console → Security credentials → MFA

3. **Check Bucket Names**: If Terraform outputs aren't available, provide bucket names manually when prompted

4. **Verify Permissions**: Root account should have full S3 permissions

### Manual Alternative

If the script doesn't work, you can enable MFA delete manually:

```bash
# Get your account ID
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# Enable MFA delete (replace MFA_CODE with your current MFA code)
aws s3api put-bucket-versioning \
  --bucket YOUR-BUCKET-NAME \
  --versioning-configuration Status=Enabled,MFADelete=Enabled \
  --mfa "arn:aws:iam::${ACCOUNT_ID}:mfa/root-account-mfa-device MFA_CODE"
```
