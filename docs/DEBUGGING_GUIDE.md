# Debugging Guide for Lambda & API Gateway

This guide explains how to use the enhanced debugging infrastructure to troubleshoot errors in your Lambda function behind API Gateway.

## Quick Access

### CloudWatch Dashboard

The main debugging dashboard is available at:

```
https://{region}.console.aws.amazon.com/cloudwatch/home?region={region}#dashboards:name={app-name}-{environment}-debug-dashboard
```

**To get the exact URL**, run:

```bash
terraform output cloudwatch_dashboard_url
```

Or find it in the AWS Console:

1. Go to **CloudWatch** → **Dashboards**
2. Look for: `{app-name}-{environment}-debug-dashboard`

## Dashboard Sections

### 1. Lambda Function Metrics

**Lambda Invocations, Errors, Throttles** (Top Left)

- Shows request volume, errors, and throttles
- **What to look for**: Sudden spikes in errors or throttles

**Lambda Duration (Avg & Max)** (Top Right)

- Shows average and maximum execution times
- **What to look for**: Duration approaching timeout (check your Lambda timeout setting)

**Lambda Concurrent Executions** (Middle Left)

- Shows how many requests are running simultaneously
- **What to look for**: Approaching account limits (1000 by default)

**Lambda Duration Percentiles** (Middle Right)

- Shows p99, p95, p50 duration metrics
- **What to look for**: High p99 indicates some requests are slow

**Lambda Error Rate** (Bottom Left)

- Compares errors vs total invocations
- **What to look for**: Error rate > 0 indicates problems

### 2. API Gateway Metrics

**API Gateway Request Count & Errors** (Top Right)

- Shows total requests, 4XX, and 5XX errors
- **What to look for**: 5XX errors indicate Lambda/backend issues

**API Gateway Average Latency** (Middle Left)

- Total time from API Gateway to response
- **What to look for**: High latency indicates slow Lambda or network issues

**API Gateway Latency Percentiles** (Middle Right)

- p99, p95, p50 latency breakdown
- **What to look for**: High p99 indicates inconsistent performance

**API Gateway Error Breakdown** (Bottom Left)

- 4XX vs 5XX errors
- **What to look for**: 4XX = client errors, 5XX = server errors

**API Gateway vs Integration Latency** (Bottom Right)

- Compares total latency vs Lambda execution time
- **What to look for**: Large gap indicates API Gateway overhead

### 3. CloudWatch Logs Insights

**Recent Lambda Errors (Last 100)**

- Shows the most recent errors from Lambda logs
- **How to use**: Click on an error to see full details
- **What to look for**: Error messages, stack traces, request IDs

**Recent API Gateway Errors (Last 100)**

- Shows errors from API Gateway access logs
- **How to use**: Click to see request details, status codes, error messages
- **What to look for**: Integration errors, timeout errors

**Top Error Request IDs**

- Groups errors by request ID to find patterns
- **How to use**: Click a request ID to see all related errors
- **What to look for**: Request IDs with multiple errors indicate retries or cascading failures

## Using Structured Logs

### Viewing Logs in CloudWatch

1. Go to **CloudWatch** → **Log groups**
2. Find: `/aws/lambda/{app-name}-{environment}`
3. Click on a log stream to view logs

### Log Format

Logs are now in structured JSON format:

```json
{
  "timestamp": "2024-01-15T10:30:45.123Z",
  "level": "ERROR",
  "message": "Lambda request failed: Database connection error",
  "module": "lambda_handler",
  "function": "lambda_handler",
  "line": 245,
  "request_id": "abc123-def456",
  "lambda_request_id": "req-789",
  "path": "/api/expenses",
  "method": "POST",
  "status_code": 500,
  "duration_ms": 1234.56,
  "xray_trace_id": "1-abc123-def456",
  "exception": {
    "type": "DatabaseError",
    "message": "Connection timeout",
    "traceback": ["..."]
  }
}
```

### Searching Logs

Use CloudWatch Logs Insights to search:

**Find all errors in the last hour:**

```
SOURCE '/aws/lambda/{app-name}-{environment}'
| fields @timestamp, @message, request_id, path, method
| filter level = "ERROR"
| sort @timestamp desc
```

**Find errors for a specific request:**

```
SOURCE '/aws/lambda/{app-name}-{environment}'
| fields @timestamp, @message
| filter request_id = "abc123-def456"
| sort @timestamp desc
```

**Find slow requests (>5 seconds):**

```
SOURCE '/aws/lambda/{app-name}-{environment}'
| fields @timestamp, @message, duration_ms, path
| filter duration_ms > 5000
| sort duration_ms desc
```

## CloudWatch Alarms

### Viewing Alarms

1. Go to **CloudWatch** → **Alarms**
2. Filter by: `{app-name}-{environment}`

### Alarm Types

**Lambda Alarms:**

- `{app-name}-{environment}-lambda-errors`: Triggers when errors exceed threshold
- `{app-name}-{environment}-lambda-throttles`: Triggers on throttles
- `{app-name}-{environment}-lambda-duration`: Triggers on slow executions
- `{app-name}-{environment}-lambda-concurrent`: Triggers on high concurrency

**API Gateway Alarms:**

- `{app-name}-{environment}-api-4xx-errors`: Client errors
- `{app-name}-{environment}-api-5xx-errors`: Server errors
- `{app-name}-{environment}-api-latency`: High latency

### Alarm Notifications

Alarms send notifications to the SNS topic: `{app-name}-{environment}-notifications`

**To set up email notifications:**

1. Go to **SNS** → **Topics**
2. Find: `{app-name}-{environment}-notifications`
3. Click **Create subscription**
4. Choose **Email** and enter your email
5. Confirm the subscription email

## Debugging Workflow

### When an Error Occurs

1. **Check the Dashboard**

   - Look at the "Recent Lambda Errors" widget
   - Note the request ID and timestamp

2. **View Detailed Logs**

   - Go to CloudWatch Logs
   - Search for the request ID
   - Review the full error traceback

3. **Check API Gateway Logs**

   - Look at "Recent API Gateway Errors"
   - Check integration status and error messages
   - Verify request reached Lambda

4. **Use X-Ray (if enabled)**

   - Click the X-Ray trace ID from logs
   - View the service map
   - See timing breakdown

5. **Check Alarms**
   - See if any alarms are in ALARM state
   - Review alarm history for patterns

### Debugging a Specific 500 Error

**Example: API Gateway shows status 500 with request ID `VJVxojh4IAMEZJw=`**

1. **Find the corresponding Lambda log entry:**

   ```
   SOURCE '/aws/lambda/meal-expense-tracker-dev'
   | fields @timestamp, @message, request_id, lambda_request_id, exception
   | filter request_id = "VJVxojh4IAMEZJw=" or api_request_id = "VJVxojh4IAMEZJw="
   | sort @timestamp desc
   ```

2. **Or search by timestamp (around 03:02:46 UTC):**

   ```
   SOURCE '/aws/lambda/meal-expense-tracker-dev'
   | fields @timestamp, @message, request_id, path, method, exception
   | filter @timestamp >= 1764990166000 and @timestamp <= 1764990168000
   | filter level = "ERROR" or status_code = 500
   | sort @timestamp desc
   ```

3. **Check what the Lambda actually returned:**

   - The API Gateway log shows `responseLength: 33305`, meaning Lambda responded
   - This suggests Lambda returned an error response (likely HTML error page)
   - Look for the Lambda log entry with the actual exception

4. **Common causes for 500 errors:**

   - **Unhandled exception in Lambda**: Check Lambda logs for stack trace
   - **Timeout**: Check if duration_ms is near your Lambda timeout
   - **Memory limit**: Check if Lambda ran out of memory
   - **Database connection error**: Look for database-related exceptions
   - **Import error**: Check for missing dependencies or import failures

5. **If integrationError is "-" in API Gateway:**

   - This means API Gateway successfully called Lambda
   - The error is coming from Lambda's response
   - Focus on Lambda logs, not API Gateway logs

### Common Issues

**High Error Rate:**

1. Check "Lambda Error Rate" widget
2. View "Recent Lambda Errors" for patterns
3. Check if errors are time-based (indicates resource limits)
4. Review error messages for common causes

**Slow Performance:**

1. Check "Lambda Duration Percentiles"
2. Look for requests with high `duration_ms` in logs
3. Check "API Gateway vs Integration Latency" to isolate where slowness occurs
4. Review X-Ray traces for bottlenecks

**Throttling:**

1. Check "Lambda Concurrent Executions"
2. Review "Lambda Throttles" metric
3. Consider increasing Lambda concurrency limits
4. Check if errors are causing retries (increasing load)

**5XX Errors:**

1. Check "API Gateway Error Breakdown"
2. View "Recent API Gateway Errors" for integration errors
3. Check Lambda logs for exceptions
4. Verify Lambda timeout isn't being exceeded

## Advanced Debugging

### Using X-Ray Traces

If X-Ray is enabled:

1. **Find Trace ID** in Lambda logs: `xray_trace_id`
2. Go to **X-Ray** → **Traces**
3. Search for the trace ID
4. View:
   - Service map showing all components
   - Timeline showing where time was spent
   - Annotations with error details
   - Metadata with request context

### Custom Log Queries

Create saved queries in CloudWatch Logs Insights:

**Error Rate Over Time:**

```
SOURCE '/aws/lambda/{app-name}-{environment}'
| fields @timestamp
| filter level = "ERROR"
| stats count() by bin(5m)
```

**Top Error Types:**

```
SOURCE '/aws/lambda/{app-name}-{environment}'
| fields exception.type, exception.message
| filter ispresent(exception.type)
| stats count() by exception.type
| sort count desc
```

**Request Duration Distribution:**

```
SOURCE '/aws/lambda/{app-name}-{environment}'
| fields duration_ms
| stats count() by bin(1000ms)
| sort duration_ms asc
```

**Find all 500 errors in the last hour:**

```
SOURCE '/aws/lambda/{app-name}-{environment}'
| fields @timestamp, @message, request_id, path, method, exception
| filter status_code = 500 or level = "ERROR"
| sort @timestamp desc
| limit 100
```

## Best Practices

1. **Monitor Regularly**: Check the dashboard daily for trends
2. **Set Up Alerts**: Subscribe to SNS notifications for critical alarms
3. **Use Request IDs**: Always include request IDs when reporting issues
4. **Check Logs First**: Start with CloudWatch Logs Insights queries
5. **Use X-Ray**: Enable X-Ray in production for detailed tracing
6. **Review Patterns**: Look for time-based patterns in errors
7. **Document Common Issues**: Keep notes on frequent errors and solutions

## Getting Help

When reporting issues, include:

- Request ID from logs
- X-Ray trace ID (if available)
- Timestamp of the error
- Error message and stack trace
- Relevant dashboard screenshots
- Any alarm notifications received
