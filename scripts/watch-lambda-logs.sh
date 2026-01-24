#!/bin/bash
# Watch Lambda CloudWatch logs

LOG_GROUP="/aws/lambda/meal-expense-tracker-dev"

# Allow optional filter pattern as first argument
FILTER_PATTERN="${1:-}"

echo "Watching CloudWatch logs for: $LOG_GROUP"
if [ -n "$FILTER_PATTERN" ]; then
    echo "Filter pattern: $FILTER_PATTERN"
    echo "Usage: $0 [filter-pattern]"
    echo "Example: $0 'error|exception|receipt'"
fi
echo "Press Ctrl+C to stop"
echo "=========================================="
echo ""

# Use aws logs tail with optional filter
if [ -n "$FILTER_PATTERN" ]; then
    aws logs tail "$LOG_GROUP" --follow --format short 2>&1 | grep --line-buffered -i -E "$FILTER_PATTERN" || {
        echo ""
        echo "If filtering doesn't work, try viewing all logs:"
        echo "aws logs tail $LOG_GROUP --follow --format short"
        echo ""
        echo "Or view recent logs:"
        echo "aws logs tail $LOG_GROUP --since 10m --format short"
    }
else
    aws logs tail "$LOG_GROUP" --follow --format short 2>&1 || {
        echo ""
        echo "Error: Could not tail logs. Check that:"
        echo "  1. AWS CLI is installed and configured"
        echo "  2. You have permissions to read CloudWatch logs"
        echo "  3. The log group exists: $LOG_GROUP"
        echo ""
        echo "To view recent logs instead:"
        echo "aws logs tail $LOG_GROUP --since 10m --format short"
        echo ""
        echo "To filter logs, pass a pattern as argument:"
        echo "$0 'error|exception|receipt'"
    }
fi
