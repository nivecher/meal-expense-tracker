#!/bin/bash
# Watch Lambda CloudWatch logs for profile updates

LOG_GROUP="/aws/lambda/meal-expense-tracker-dev"

echo "Watching CloudWatch logs for: $LOG_GROUP"
echo "Try saving your profile now and watch for log entries..."
echo "Press Ctrl+C to stop"
echo ""
echo "Filtering for: profile, user, login, exception, error, Starting, committed"
echo "=========================================="
echo ""

# Try using aws logs tail (newer AWS CLI versions)
if aws logs tail --help &>/dev/null; then
    aws logs tail "$LOG_GROUP" --follow --format short | grep -i -E "(profile|user|login|exception|error|Starting|committed|After commit|EXCEPTION|Profile route|Profile update)" --color=always
else
    # Fallback for older AWS CLI versions
    echo "Using filter-log-events (older AWS CLI)..."
    START_TIME=$(($(date +%s) - 300))000  # 5 minutes ago
    aws logs filter-log-events \
        --log-group-name "$LOG_GROUP" \
        --start-time "$START_TIME" \
        --filter-pattern "profile" \
        --query 'events[*].[timestamp,message]' \
        --output text | while read timestamp message; do
            echo "[$(date -d @$((timestamp/1000)))] $message"
        done
fi
