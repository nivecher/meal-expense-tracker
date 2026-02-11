# AWS WAF Configuration for CloudFront

## Overview

This document explains the AWS WAF (Web Application Firewall) configuration for the CloudFront distribution, including free tier options and cost optimization strategies.

## Free Tier Options

### 1. Bot Control Managed Rule Group (FREE)

- **Free Tier**: Up to 10 million requests per month
- **What it does**: Protects against automated traffic, bots, and scrapers
- **Status**: ✅ Enabled by default when `enable_waf = true`

### 2. CloudFront Flat-Rate Pricing Plans

- **Free Plan**: Includes WAF, DDoS protection, and other services bundled
- **Note**: This is a CloudFront-level feature, not a WAF-specific configuration
- **Status**: Can be enabled in AWS Console for CloudFront distributions

## Current Configuration

### Default Setup (Free Tier Optimized)

The WAF is configured with:

1. **Bot Control Rule Set** (FREE)
   - Priority: 1
   - Action: Block detected bots
   - Free for up to 10M requests/month

2. **Common Rule Set** (Optional, Standard Pricing)
   - Priority: 2
   - Action: Block common web exploits
   - Cost: $1/month + $0.60 per million requests
   - **Status**: Disabled by default (`waf_include_common_ruleset = false`)

### Configuration Variables

```hcl
# Enable/disable WAF entirely
enable_waf = true  # Default: true

# Include Common Rule Set (has standard pricing)
waf_include_common_ruleset = false  # Default: false (free tier only)
```

## Cost Breakdown

### Free Tier Configuration (Default)

- **Bot Control**: FREE (10M requests/month)
- **Web ACL**: $5/month (standard pricing)
- **Total**: ~$5/month + $0.60 per million requests over 10M

### With Common Rule Set

- **Bot Control**: FREE (10M requests/month)
- **Common Rule Set**: $1/month + $0.60 per million requests
- **Web ACL**: $5/month
- **Total**: ~$6/month + $0.60 per million requests over 10M

### Cost Optimization Tips

1. **Start with Free Tier Only**: Use only Bot Control initially
2. **Monitor Traffic**: Track request volume to stay within 10M/month
3. **Enable Common Rule Set Only When Needed**: Add it if you need additional protection
4. **Consider CloudFront Flat-Rate Plans**: May be more cost-effective for high traffic

## Implementation Details

### WAF Web ACL Location

- **Region**: us-east-1 (required for CloudFront)
- **Scope**: CLOUDFRONT
- **Provider**: Uses `aws.us-east-1` provider alias

### CloudWatch Metrics

- Bot Control metrics: `BotControlRule`
- Common Rule Set metrics: `CommonRuleSet`
- Overall WAF metrics: `{app_name}-{environment}-waf`

### Default Action

- **Action**: Allow (default)
- **Behavior**: Requests that don't match any rules are allowed through

## Enabling/Disabling WAF

### Disable WAF Entirely

```hcl
module "cloudfront" {
  # ... other configuration ...
  enable_waf = false
}
```

### Enable with Common Rule Set

```hcl
module "cloudfront" {
  # ... other configuration ...
  enable_waf                  = true
  waf_include_common_ruleset  = true
}
```

## Monitoring and Alerts

### CloudWatch Metrics to Monitor

1. **Request Count**: Track total requests to stay within free tier
2. **Blocked Requests**: Monitor how many requests are being blocked
3. **Bot Detection**: Track bot traffic patterns

### Recommended Alerts

- Alert when request count approaches 10M/month (free tier limit)
- Alert on high blocked request rates (potential attack)
- Alert on unusual traffic patterns

## Best Practices

1. **Start Small**: Begin with Bot Control only (free tier)
2. **Monitor First**: Watch metrics for 1-2 weeks before adding rules
3. **Gradual Rollout**: Enable Common Rule Set in monitoring mode first
4. **Review Blocked Requests**: Regularly check what's being blocked
5. **Adjust Rules**: Fine-tune rules based on your application's needs

## Troubleshooting

### WAF Not Blocking Requests

- Check that `enable_waf = true`
- Verify Web ACL is attached to CloudFront distribution
- Review CloudWatch metrics to see if rules are evaluating

### High Costs

- Check request volume (may exceed 10M/month free tier)
- Disable Common Rule Set if not needed
- Consider CloudFront flat-rate pricing plans

### False Positives

- Review blocked requests in CloudWatch logs
- Adjust rule actions (use "Count" mode for testing)
- Create custom allow rules for legitimate traffic

## References

- [AWS WAF Pricing](https://aws.amazon.com/waf/pricing/)
- [Bot Control Managed Rule Group](https://docs.aws.amazon.com/waf/latest/developerguide/aws-managed-rule-groups-bot.html)
- [CloudFront Flat-Rate Pricing Plans](https://docs.aws.amazon.com/waf/latest/developerguide/waf-cf-pricing-plans.html)
- [AWS WAF for CloudFront](https://docs.aws.amazon.com/waf/latest/developerguide/cloudfront-features.html)
