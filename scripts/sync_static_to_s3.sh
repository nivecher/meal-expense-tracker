#!/bin/bash
# Sync Static Files to S3 for CloudFront
# This script uploads static assets to S3 for CloudFront distribution

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Source environment variables
ENVIRONMENT="${ENVIRONMENT:-dev}"
AWS_REGION="${AWS_REGION:-us-east-1}"
PROFILE="${AWS_PROFILE:-}"

# S3 bucket name
BUCKET_NAME="meal-expense-tracker-${ENVIRONMENT}-static"

# CloudFront distribution ID (prefer explicit env var)
CLOUDFRONT_DISTRIBUTION_ID="${CLOUDFRONT_DISTRIBUTION_ID:-}"

# Function to log
log() {
    echo -e "${GREEN}[*]${NC} $1"
}

log_error() {
    echo -e "${RED}[!]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

get_cloudfront_distribution_id() {
    if [ -n "${CLOUDFRONT_DISTRIBUTION_ID}" ]; then
        echo "${CLOUDFRONT_DISTRIBUTION_ID}"
        return 0
    fi

    local s3_origin="${BUCKET_NAME}.s3.amazonaws.com"
    local s3_regional_origin="${BUCKET_NAME}.s3.${AWS_REGION}.amazonaws.com"
    local s3_website_origin="${BUCKET_NAME}.s3-website-${AWS_REGION}.amazonaws.com"
    local distribution_id=""

    distribution_id="$(aws cloudfront list-distributions \
        ${PROFILE:+--profile $PROFILE} \
        --query "DistributionList.Items[?Origins.Items[?DomainName=='${s3_origin}']].Id | [0]" \
        --output text 2>/dev/null || true)"

    if [ -z "${distribution_id}" ] || [ "${distribution_id}" = "None" ]; then
        distribution_id="$(aws cloudfront list-distributions \
            ${PROFILE:+--profile $PROFILE} \
            --query "DistributionList.Items[?Origins.Items[?DomainName=='${s3_regional_origin}']].Id | [0]" \
            --output text 2>/dev/null || true)"
    fi

    if [ -z "${distribution_id}" ] || [ "${distribution_id}" = "None" ]; then
        distribution_id="$(aws cloudfront list-distributions \
            ${PROFILE:+--profile $PROFILE} \
            --query "DistributionList.Items[?Origins.Items[?DomainName=='${s3_website_origin}']].Id | [0]" \
            --output text 2>/dev/null || true)"
    fi

    if [ "${distribution_id}" = "None" ]; then
        distribution_id=""
    fi

    echo "${distribution_id}"
    return 0
}

validate_cloudfront_distribution() {
    local distribution_id="$1"
    if [ -z "${distribution_id}" ]; then
        return 1
    fi

    aws cloudfront get-distribution \
        --id "${distribution_id}" \
        ${PROFILE:+--profile $PROFILE} \
        &> /dev/null
}

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    log_error "AWS CLI is not installed. Please install it first."
    exit 1
fi

# Check AWS credentials
log "Checking AWS credentials..."
if ! aws sts get-caller-identity ${PROFILE:+--profile $PROFILE} &> /dev/null; then
    log_error "AWS credentials not configured. Please run 'aws configure'."
    exit 1
fi

# Check if bucket exists
log "Checking if bucket ${BUCKET_NAME} exists..."
if ! aws s3 ls "s3://${BUCKET_NAME}" ${PROFILE:+--profile $PROFILE} &> /dev/null; then
    log_warning "Bucket ${BUCKET_NAME} does not exist. Please run Terraform first."
    exit 1
fi

# Sync static files to S3
log "Syncing static files to S3..."
STATIC_DIR="${PROJECT_ROOT}/app/static"

if [ ! -d "${STATIC_DIR}" ]; then
    log_error "Static directory not found: ${STATIC_DIR}"
    exit 1
fi

# Upload files with proper cache headers
log "Uploading static files with cache headers..."

# Upload CSS files with long-term caching
if [ -d "${STATIC_DIR}/css" ]; then
    log "Uploading CSS files..."
    aws s3 sync "${STATIC_DIR}/css" "s3://${BUCKET_NAME}/static/css" \
        --cache-control "public, max-age=31536000, immutable" \
        --content-type "text/css" \
        --exclude "*.map" \
        ${PROFILE:+--profile $PROFILE}
fi

# Upload JS files with long-term caching
if [ -d "${STATIC_DIR}/js" ]; then
    log "Uploading JS files..."
    aws s3 sync "${STATIC_DIR}/js" "s3://${BUCKET_NAME}/static/js" \
        --cache-control "public, max-age=31536000, immutable" \
        --content-type "application/javascript" \
        --exclude "*.map" \
        ${PROFILE:+--profile $PROFILE}
fi

# Upload image files with long-term caching
if [ -d "${STATIC_DIR}/img" ]; then
    log "Uploading image files..."
    aws s3 sync "${STATIC_DIR}/img" "s3://${BUCKET_NAME}/static/img" \
        --cache-control "public, max-age=31536000, immutable" \
        ${PROFILE:+--profile $PROFILE}
fi

# Upload data files with moderate caching
if [ -d "${STATIC_DIR}/data" ]; then
    log "Uploading data files..."
    aws s3 sync "${STATIC_DIR}/data" "s3://${BUCKET_NAME}/static/data" \
        --cache-control "public, max-age=86400" \
        ${PROFILE:+--profile $PROFILE}
fi

# Upload other files
log "Uploading other static files..."
aws s3 sync "${STATIC_DIR}" "s3://${BUCKET_NAME}/static" \
    --exclude "*.map" \
    --exclude "uploads/*" \
    --cache-control "public, max-age=3600" \
    ${PROFILE:+--profile $PROFILE}

log "Static files uploaded successfully!"

# Invalidate CloudFront cache
log "Invalidating CloudFront cache..."
CF_ID="$(get_cloudfront_distribution_id)"
if [ -n "${CF_ID}" ]; then
    if validate_cloudfront_distribution "${CF_ID}"; then
        log "Creating CloudFront invalidation for distribution ${CF_ID}..."
        aws cloudfront create-invalidation \
            --distribution-id "${CF_ID}" \
            --paths "/static/*" \
            ${PROFILE:+--profile $PROFILE} || log_warning "Could not invalidate CloudFront cache"
        log "CloudFront invalidation request sent successfully"
    else
        log_warning "CloudFront distribution ${CF_ID} not found or not accessible"
    fi
else
    log_warning "CloudFront distribution ID not provided. Set CLOUDFRONT_DISTRIBUTION_ID or run Terraform."
fi

log "Done!"
