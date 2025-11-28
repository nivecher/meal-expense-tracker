#!/bin/bash
# Enable MFA Delete on S3 Buckets
# This script enables MFA delete protection on S3 buckets using AWS CLI
# Note: This requires root account credentials and an MFA device

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
TERRAFORM_DIR="${PROJECT_ROOT}/terraform"

# Function to print colored output
print_info() {
  echo -e "${GREEN}[INFO]${NC} $1"
}

print_warn() {
  echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
  echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if command exists
command_exists() {
  command -v "$1" >/dev/null 2>&1
}

# Check prerequisites
check_prerequisites() {
  print_info "Checking prerequisites..."

  if ! command_exists aws; then
    print_error "AWS CLI is not installed. Please install it first."
    exit 1
  fi

  if ! command_exists terraform; then
    print_error "Terraform is not installed. Please install it first."
    exit 1
  fi

  # Check if AWS credentials are configured
  if ! aws sts get-caller-identity >/dev/null 2>&1; then
    print_error "AWS credentials are not configured. Please run 'aws configure' first."
    exit 1
  fi

  print_info "Prerequisites check passed."
}

# Get AWS account ID
get_account_id() {
  local account_id
  account_id=$(aws sts get-caller-identity --query Account --output text 2>/dev/null || echo "")

  if [ -z "${account_id}" ]; then
    print_error "Failed to get AWS account ID. Please check your AWS credentials."
    exit 1
  fi

  echo "${account_id}"
}

# Get bucket names from Terraform outputs
get_bucket_names() {
  local terraform_dir="${1}"
  local environment="${2:-}"

  # Try to get bucket names from Terraform outputs
  if [ -d "${terraform_dir}" ]; then
    cd "${terraform_dir}" || exit 1

    # Initialize Terraform if needed
    if [ ! -d ".terraform" ]; then
      print_info "Initializing Terraform..."
      terraform init -backend=false >/dev/null 2>&1 || true
    fi

    # Try to get outputs (may fail if not applied)
    local receipts_bucket
    local logs_bucket

    receipts_bucket=$(terraform output -raw receipts_bucket_name 2>/dev/null || echo "")
    logs_bucket=$(terraform output -raw logs_bucket_id 2>/dev/null || echo "")

    if [ -n "${receipts_bucket}" ] && [ -n "${logs_bucket}" ]; then
      echo "${receipts_bucket}|${logs_bucket}"
      return 0
    fi
  fi

  return 1
}

# Prompt for bucket names manually
prompt_bucket_names() {
  local receipts_bucket
  local logs_bucket

  echo ""
  print_info "Please provide bucket names manually:"
  read -rp "Receipts bucket name: " receipts_bucket
  read -rp "Logs bucket name (press Enter to skip): " logs_bucket

  if [ -z "${receipts_bucket}" ]; then
    print_error "Receipts bucket name is required."
    exit 1
  fi

  echo "${receipts_bucket}|${logs_bucket}"
}

# Prompt for MFA code
prompt_mfa_code() {
  local mfa_code
  echo ""
  print_info "Please enter your MFA code from your device:"
  print_warn "Note: MFA codes are time-sensitive. Enter the current code from your device."
  read -rsp "MFA Code: " mfa_code
  echo ""

  if [ -z "${mfa_code}" ]; then
    print_error "MFA code is required."
    exit 1
  fi

  # Validate MFA code format (typically 6 digits)
  if ! echo "${mfa_code}" | grep -qE '^[0-9]{6}$'; then
    print_warn "MFA code should typically be 6 digits. Continuing anyway..."
  fi

  echo "${mfa_code}"
}

# List available MFA devices
list_mfa_devices() {
  print_info "Listing available MFA devices..."
  echo ""

  # List virtual MFA devices
  local virtual_devices
  virtual_devices=$(aws iam list-virtual-mfa-devices --query "VirtualMFADevices[?User.UserName=='root'].SerialNumber" --output text 2>/dev/null || echo "")

  if [ -n "${virtual_devices}" ] && [ "${virtual_devices}" != "None" ]; then
    print_info "Virtual MFA devices found:"
    echo "${virtual_devices}" | while read -r device; do
      echo "  - ${device}"
    done
    echo ""
  fi

  # Note about hardware MFA devices
  print_info "For hardware MFA devices, the serial number format is typically:"
  print_info "  arn:aws:iam::ACCOUNT_ID:mfa/root-account-mfa-device"
  echo ""
}

# Get MFA device serial number
get_mfa_device_serial() {
  local account_id="${1}"
  local manual_serial="${2:-}"

  # Use manually provided serial if given
  if [ -n "${manual_serial}" ]; then
    echo "${manual_serial}"
    return 0
  fi

  # Try to get the MFA device serial number from IAM
  local mfa_serial
  mfa_serial=$(aws iam list-virtual-mfa-devices --query "VirtualMFADevices[?User.UserName=='root'].SerialNumber" --output text 2>/dev/null | head -n1)

  if [ -n "${mfa_serial}" ] && [ "${mfa_serial}" != "None" ]; then
    echo "${mfa_serial}"
    return 0
  fi

  # Fallback to root account MFA device format
  echo "arn:aws:iam::${account_id}:mfa/root-account-mfa-device"
  return 0
}

# Enable MFA delete on a bucket
enable_mfa_delete() {
  local bucket_name="${1}"
  local account_id="${2}"
  local mfa_code="${3}"
  local mfa_device_serial="${4:-}"

  local mfa_device_arn
  mfa_device_arn=$(get_mfa_device_serial "${account_id}" "${mfa_device_serial}")

  print_info "Enabling MFA delete on bucket: ${bucket_name}"
  print_info "Using MFA device: ${mfa_device_arn}"

  # Capture both stdout and stderr
  local error_output
  error_output=$(aws s3api put-bucket-versioning \
    --bucket "${bucket_name}" \
    --versioning-configuration "Status=Enabled,MFADelete=Enabled" \
    --mfa "${mfa_device_arn} ${mfa_code}" 2>&1)

  local exit_code=$?

  if [ ${exit_code} -eq 0 ]; then
    print_info "Successfully enabled MFA delete on ${bucket_name}"
    return 0
  else
    print_error "Failed to enable MFA delete on ${bucket_name}"
    echo ""
    print_error "AWS CLI Error:"
    echo "${error_output}" | sed 's/^/  /'
    echo ""
    print_warn "Common issues:"
    print_warn "  1. MFA device serial number might be incorrect"
    print_warn "  2. MFA code might be expired (codes are time-sensitive)"
    print_warn "  3. Root account credentials might not be configured"
    print_warn "  4. MFA device might not be configured for root account"
    echo ""
    print_info "To find your MFA device serial number, run:"
    print_info "  aws iam list-virtual-mfa-devices --query 'VirtualMFADevices[?User.UserName==\`root\`].SerialNumber' --output text"
    return 1
  fi
}

# Verify MFA delete is enabled
verify_mfa_delete() {
  local bucket_name="${1}"

  print_info "Verifying MFA delete status for ${bucket_name}..."

  local versioning_config
  versioning_config=$(aws s3api get-bucket-versioning --bucket "${bucket_name}" 2>/dev/null || echo "")

  if echo "${versioning_config}" | grep -q "MFADelete.*Enabled"; then
    print_info "✓ MFA delete is enabled on ${bucket_name}"
    return 0
  else
    print_warn "✗ MFA delete is not enabled on ${bucket_name}"
    return 1
  fi
}

# Main function
main() {
  print_info "S3 MFA Delete Enablement Script"
  print_info "================================"

  # Check prerequisites
  check_prerequisites

  # Get AWS account ID
  print_info "Getting AWS account ID..."
  local account_id
  account_id=$(get_account_id)
  print_info "AWS Account ID: ${account_id}"

  # Check if using root account
  local caller_arn
  caller_arn=$(aws sts get-caller-identity --query Arn --output text 2>/dev/null || echo "")
  if echo "${caller_arn}" | grep -q "root"; then
    print_info "Using root account credentials ✓"
  else
    print_warn "Warning: Not using root account credentials."
    print_warn "MFA delete can only be enabled with root account credentials."
    read -rp "Continue anyway? (y/N): " confirm
    if [ "${confirm}" != "y" ] && [ "${confirm}" != "Y" ]; then
      print_info "Exiting. Please use root account credentials."
      exit 0
    fi
  fi

  # Get bucket names
  local bucket_info
  local receipts_bucket
  local logs_bucket

  if bucket_info=$(get_bucket_names "${TERRAFORM_DIR}" 2>/dev/null); then
    receipts_bucket=$(echo "${bucket_info}" | cut -d'|' -f1)
    logs_bucket=$(echo "${bucket_info}" | cut -d'|' -f2)
    print_info "Found buckets from Terraform outputs:"
    print_info "  Receipts: ${receipts_bucket}"
    if [ -n "${logs_bucket}" ]; then
      print_info "  Logs: ${logs_bucket}"
    fi
  else
    print_warn "Could not get bucket names from Terraform. Please provide them manually."
    bucket_info=$(prompt_bucket_names)
    receipts_bucket=$(echo "${bucket_info}" | cut -d'|' -f1)
    logs_bucket=$(echo "${bucket_info}" | cut -d'|' -f2)
  fi

  # List MFA devices and allow manual specification
  echo ""
  list_mfa_devices
  local mfa_device_serial
  read -rp "Enter MFA device serial number (press Enter to use auto-detected): " mfa_device_serial
  if [ -z "${mfa_device_serial}" ]; then
    mfa_device_serial=""
  fi

  # Prompt for MFA code
  local mfa_code
  mfa_code=$(prompt_mfa_code)

  # Enable MFA delete on receipts bucket
  echo ""
  print_info "Enabling MFA delete on receipts bucket..."
  if ! enable_mfa_delete "${receipts_bucket}" "${account_id}" "${mfa_code}" "${mfa_device_serial}"; then
    print_error "Failed to enable MFA delete on receipts bucket."
    exit 1
  fi

  # Enable MFA delete on logs bucket (if it exists)
  if [ -n "${logs_bucket}" ] && [ "${logs_bucket}" != "" ]; then
    echo ""
    print_info "Enabling MFA delete on logs bucket..."
    if ! enable_mfa_delete "${logs_bucket}" "${account_id}" "${mfa_code}" "${mfa_device_serial}"; then
      print_warn "Failed to enable MFA delete on logs bucket (may not exist or already configured)."
    fi
  fi

  # Verify MFA delete is enabled
  echo ""
  print_info "Verifying MFA delete configuration..."
  verify_mfa_delete "${receipts_bucket}"

  if [ -n "${logs_bucket}" ] && [ "${logs_bucket}" != "" ]; then
    verify_mfa_delete "${logs_bucket}"
  fi

  echo ""
  print_info "MFA delete enablement complete!"
  print_info "================================"
  print_warn "Note: MFA delete requires root account credentials."
  print_warn "After enabling, you'll need MFA to delete objects or change versioning settings."
}

# Run main function
main "$@"
