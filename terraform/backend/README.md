# Terraform Backend Configuration

This directory contains scripts and configurations for setting up and managing the Terraform backend.

## Files

- `backend.hcl` - The generated backend configuration file (do not edit directly)
- `tf-backend.hcl.template` - Template for generating the backend configuration
- `generate-backend-config.sh` - Script to generate the backend configuration
- `setup-backend.sh` - Script to set up the S3 backend and DynamoDB table

## Setup Instructions

### Prerequisites

- AWS CLI configured with appropriate credentials
- jq installed (`sudo apt-get install jq` on Ubuntu/Debian)

### 1. Generate Backend Configuration

Run the following command to generate the backend configuration:

```bash
./generate-backend-config.sh
```

This will create a `backend.hcl` file with the appropriate values.

### 2. Set Up the Backend

Run the setup script to create the S3 bucket and DynamoDB table:

```bash
./setup-backend.sh
```

### 3. Initialize Terraform with the Backend

After setting up the backend, initialize Terraform:

```bash
cd ..
terraform init -backend-config=backend/backend.hcl
```

## Customization

Edit the `tf-backend.hcl.template` file to customize the backend configuration, then regenerate the `backend.hcl` file.

## Security Considerations

- The S3 bucket and DynamoDB table are created with encryption enabled by default
- The bucket has versioning enabled to maintain a history of state files
- The DynamoDB table is used for state locking to prevent concurrent modifications
- IAM policies should be configured to restrict access to the state files
