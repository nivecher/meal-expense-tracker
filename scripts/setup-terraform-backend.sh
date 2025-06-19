#!/bin/bash
set -euo pipefail

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Default values
STACK_NAME="terraform-backend"
REGION="us-east-1"

# Function to show recent stack failure events for easier debugging
print_stack_failures() {
  echo -e "${RED}\nStack events (recent failures):${NC}"
  aws cloudformation describe-stack-events \
    --stack-name "$STACK_NAME" \
    --region "$REGION" \
    --max-items 50 \
    --query "StackEvents[?ResourceStatus=='CREATE_FAILED' || ResourceStatus=='ROLLBACK_IN_PROGRESS' || ResourceStatus=='ROLLBACK_FAILED' || ResourceStatus=='ROLLBACK_COMPLETE'].[Timestamp,ResourceStatus,ResourceType,LogicalResourceId,ResourceStatusReason]" \
    --output table | head -n 20 || true
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
  case "$1" in
  --stack-name)
    STACK_NAME="$2"
    shift 2
    ;;
  --region)
    REGION="$2"
    shift 2
    ;;
  -h | --help)
    echo "Usage: $0 [--stack-name NAME] [--region REGION]"
    echo "  --stack-name    Name of the CloudFormation stack (default: terraform-backend)"
    echo "  --region        AWS region to deploy to (default: us-east-1)"
    exit 0
    ;;
  *)
    echo "Unknown argument: $1"
    exit 1
    ;;
  esac
done

# Get the AWS account ID
if ! AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text 2>/dev/null); then
  echo -e "${RED}Failed to get AWS account ID. Are you logged in to AWS?${NC}"
  exit 1
fi

echo -e "${GREEN}AWS Account ID: ${AWS_ACCOUNT_ID}${NC}"

echo -e "${GREEN}Setting up Terraform backend in AWS account: ${AWS_ACCOUNT_ID} (${REGION})${NC}"

# Function to check stack existence and set appropriate action
check_stack_exists() {
  # Initialize variables with default values
  local update_mode=false
  local action="create-stack"
  local wait_action="stack-create-complete"

  if aws cloudformation describe-stacks --stack-name "$1" --region "$2" &>/dev/null; then
    echo -e "${YELLOW}Stack '$1' already exists. Updating...${NC}"
    update_mode=true
    action="update-stack"
    wait_action="stack-update-complete"
  else
    echo -e "${GREEN}Creating new stack '$1'...${NC}"
  fi

  # Export variables
  export UPDATE_MODE=$update_mode
  export ACTION=$action
  export WAIT_ACTION=$wait_action
}

# Check if stack already exists
echo -e "${YELLOW}Checking if CloudFormation stack '$STACK_NAME' exists...${NC}"
check_stack_exists "$STACK_NAME" "$REGION"

# Ensure CloudFormation template directory exists
if [ ! -f "$(pwd)/cloudformation/terraform-backend.yml" ]; then
  echo -e "${RED}Error: CloudFormation template not found at $(pwd)/cloudformation/terraform-backend.yml${NC}"
  exit 1
fi

# Deploy CloudFormation stack
echo -e "${YELLOW}Deploying CloudFormation stack...${NC}"
if aws cloudformation deploy \
  --stack-name "$STACK_NAME" \
  --region "$REGION" \
  --template-file "$(pwd)/cloudformation/terraform-backend.yml" \
  --parameter-overrides "EnvironmentName=dev" \
  --capabilities CAPABILITY_NAMED_IAM; then
  echo -e "${GREEN}CloudFormation stack deployed successfully!${NC}"
else
  echo -e "${RED}Failed to deploy CloudFormation stack${NC}"
  print_stack_failures
  exit 1
fi

# Get stack outputs
echo -e "${YELLOW}Getting stack outputs...${NC}"
STATE_BUCKET=$(aws cloudformation describe-stacks \
  --stack-name "$STACK_NAME" \
  --region "$REGION" \
  --query "Stacks[0].Outputs[?OutputKey=='StateBucketName'].OutputValue" \
  --output text)

LOCK_TABLE=$(aws cloudformation describe-stacks \
  --stack-name "$STACK_NAME" \
  --region "$REGION" \
  --query "Stacks[0].Outputs[?OutputKey=='StateLockTableName'].OutputValue" \
  --output text)

echo -e "${GREEN}Terraform Backend Configuration:${NC}"
echo "S3 Bucket: $STATE_BUCKET"
echo "DynamoDB Table: $LOCK_TABLE"
echo "Region: $REGION"

# Create backend configuration for each environment
for ENV in dev staging prod; do
  echo -e "\n${YELLOW}Configuring backend for $ENV environment...${NC}"

  BACKEND_FILE="terraform/environments/$ENV/backend.hcl"

  # Create backend.hcl
  cat >"$BACKEND_FILE" <<-EOM
# Backend configuration for $ENV environment
bucket         = "$STATE_BUCKET"
key            = "$ENV/terraform.tfstate"
region         = "$REGION"
use_lockfile   = true
encrypt        = true
EOM

  echo -e "${GREEN}Created backend configuration: $BACKEND_FILE${NC}"

  # Initialize Terraform
  if [ -d "terraform/environments/$ENV" ]; then
    echo -e "${YELLOW}Initializing Terraform for $ENV...${NC}"
    cd "terraform/environments/$ENV"
    terraform init -reconfigure -backend-config=backend.hcl
    cd ../../..
  else
    echo -e "${YELLOW}Directory terraform/environments/$ENV not found. Skipping Terraform init.${NC}"
  fi
done

echo -e "\n${GREEN}✅ Terraform backend setup complete!${NC}"
echo -e "\nNext steps:"
echo "1. Review the backend configuration in each environment's backend.hcl file"
echo "2. Run 'terraform plan' in each environment directory to verify the setup"
echo "3. Commit the backend configuration files to version control"

# Create a convenience script for switching environments
cat >scripts/use-environment.sh <<'EOL'
#!/bin/bash
set -e

if [ $# -ne 1 ]; then
  echo "Usage: $0 <environment>"
  echo "Available environments: dev, staging, prod"
  exit 1
fi

ENV=$1
ENV_DIR="terraform/environments/$ENV"

if [ ! -d "$ENV_DIR" ]; then
  echo "Error: Environment '$ENV' not found in $ENV_DIR"
  exit 1
fi

echo "Switching to $ENV environment..."
cd "$ENV_DIR"

# Initialize Terraform if not already initialized
if [ ! -d ".terraform" ]; then
  echo "Initializing Terraform..."
  terraform init -backend-config=backend.hcl
fi

echo "Environment '$ENV' is ready. You can now run terraform commands."
echo "Example: terraform plan -var-file=terraform.tfvars"
EOL

chmod +x scripts/use-environment.sh

echo -e "\n${GREEN}Created convenience script: scripts/use-environment.sh${NC}"
echo "Use it to quickly switch between environments:"
echo "  ./scripts/use-environment.sh dev"
echo "  ./scripts/use-environment.sh staging"
echo "  ./scripts/use-environment.sh prod"
