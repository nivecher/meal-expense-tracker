#!/bin/bash
# Watch Lambda CloudWatch logs.
# Usage: ./scripts/watch-lambda-logs.sh [filter-pattern]
# Example: ./scripts/watch-lambda-logs.sh 'error|exception|Traceback'
# Filter terms (pipe-separated) are converted to CloudWatch ?term syntax.
# Env: LOG_GROUP, AWS_REGION (defaults: ...-dev, us-east-1).

set -euo pipefail

LOG_GROUP="${LOG_GROUP:-/aws/lambda/meal-expense-tracker-dev}"
REGION="${AWS_REGION:-us-east-1}"
FILTER_PATTERN="${1:-}"

echo "Watching CloudWatch logs for: $LOG_GROUP (region: $REGION)"
if [ -n "$FILTER_PATTERN" ]; then
    echo "Filter pattern: $FILTER_PATTERN"
fi
echo "Press Ctrl+C to stop"
echo "=========================================="
echo ""

# Pre-flight: verify we can reach CloudWatch and the log group exists
if ! aws logs describe-log-groups \
    --log-group-name-prefix "$LOG_GROUP" \
    --region "$REGION" \
    --query "logGroups[?logGroupName=='$LOG_GROUP'].logGroupName" \
    --output text 2>/dev/null | grep -q "^$LOG_GROUP$"; then
    echo "Error: Cannot reach CloudWatch or log group does not exist."
    echo "  1. Ensure AWS CLI is installed and configured: aws sts get-caller-identity"
    echo "  2. Set region if needed: AWS_REGION=us-east-1 $0"
    echo "  3. Check log group exists: aws logs describe-log-groups --log-group-name-prefix /aws/lambda/meal-expense --region $REGION"
    echo ""
    echo "To tail a different group: LOG_GROUP=/aws/lambda/my-func $0"
    exit 1
fi

# Build aws logs tail args
TAIL_ARGS=(
    "$LOG_GROUP"
    --follow
    --format short
    --since 1m
    --region "$REGION"
    --no-cli-pager
)

# Convert pipe-separated filter (e.g. error|exception|receipt) to CloudWatch ?term ?term ...
if [ -n "$FILTER_PATTERN" ]; then
    CW_PATTERN=$(echo "$FILTER_PATTERN" | tr '|' '\n' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//' | grep -v '^$' | sed 's/^/?/' | tr '\n' ' ' | sed 's/ $//')
    if [ -n "$CW_PATTERN" ]; then
        TAIL_ARGS+=(--filter-pattern "$CW_PATTERN")
    fi
fi

aws logs tail "${TAIL_ARGS[@]}" || {
    ec=$?
    echo ""
    echo "Error: aws logs tail failed (exit $ec)."
    echo "  Check AWS credentials and network connectivity."
    echo "  Try: aws logs tail $LOG_GROUP --since 10m --format short --region $REGION"
    exit $ec
}
