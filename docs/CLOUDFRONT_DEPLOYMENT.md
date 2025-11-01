# CloudFront + S3 Static Files Deployment Guide

## Overview

This guide explains how to deploy static files to S3 and serve them via CloudFront in the meal expense tracker application.

## Architecture

```
User Request → CloudFront → S3 Bucket → Static Files
```

Static assets (CSS, JS, images) are served from S3 via CloudFront CDN instead of through Lambda, providing:

- ⚡ 50-90% faster load times
- 💰 Cost-effective ($0.30/month for typical usage)
- 🚀 Better scalability
- ✅ Eliminates 503 errors on static files

## Prerequisites

- AWS CLI configured with appropriate credentials
- Terraform installed
- S3 bucket and CloudFront distribution already created by Terraform

## Deployment Steps

### 1. Deploy Infrastructure

First, deploy the Terraform infrastructure which creates:

- S3 bucket for static files
- CloudFront distribution
- Origin Access Control (OAC)

```bash
cd terraform
terraform init
terraform plan
terraform apply
```

### 2. Get CloudFront Information

Get the CloudFront distribution ID from Terraform output:

```bash
cd terraform
terraform output cloudfront_static_cloudfront_distribution_id
terraform output cloudfront_static_cloudfront_url
```

### 3. Sync Static Files to S3

Sync static files from your local `app/static` directory to S3:

```bash
./scripts/sync_static_to_s3.sh
```

This script will:

- ✅ Check AWS credentials
- ✅ Verify S3 bucket exists
- ✅ Upload CSS files with long-term caching headers
- ✅ Upload JS files with long-term caching headers
- ✅ Upload image files with long-term caching headers
- ✅ Upload other static files
- ✅ Invalidate CloudFront cache (if distribution ID found)

### 4. Verify Deployment

Check that files are in S3:

```bash
aws s3 ls s3://meal-expense-tracker-${ENVIRONMENT}-static/ --recursive
```

Check CloudFront distribution:

```bash
aws cloudfront get-distribution --id <DISTRIBUTION_ID>
```

### 5. Test in Browser

After deployment, CloudFront domain will be in Lambda environment variables:

```bash
aws lambda get-function-configuration \
  --function-name meal-expense-tracker-${ENVIRONMENT} \
  --query 'Environment.Variables.STATIC_CDN_URL'
```

Visit your application and check browser DevTools Network tab:

- Static files should load from CloudFront domain
- Check response headers show `CF-Cache-Status: HIT` after first load

## File Upload Configuration

The sync script uploads different file types with appropriate cache headers:

### CSS Files

- Cache-Control: `public, max-age=31536000, immutable`
- Content-Type: `text/css`
- Cached for 1 year

### JavaScript Files

- Cache-Control: `public, max-age=31536000, immutable`
- Content-Type: `application/javascript`
- Cached for 1 year

### Images

- Cache-Control: `public, max-age=31536000, immutable`
- Cached for 1 year

### Data Files

- Cache-Control: `public, max-age=86400`
- Cached for 1 day

## Cache Invalidation

When you update static files, invalidate CloudFront cache:

```bash
./scripts/sync_static_to_s3.sh
```

The script automatically invalidates CloudFront cache after upload.

Or manually:

```bash
aws cloudfront create-invalidation \
  --distribution-id <DISTRIBUTION_ID> \
  --paths "/*"
```

## Template Usage

In your Jinja2 templates, use the `get_static_url` function:

```html
<!-- Old way (serves from Lambda) -->
<link
  rel="stylesheet"
  href="{{ url_for('static', filename='css/main.css') }}"
/>

<!-- New way (serves from CloudFront CDN) -->
<link
  rel="stylesheet"
  href="{{ get_static_url('css/main.css', static_cdn_url) }}"
/>
```

Note: The `static_cdn_url` variable is automatically injected into all templates by the `inject_cdn_url()` context processor.

## Environment Variables

The CloudFront URL is automatically configured via Terraform in the Lambda environment:

```python
# In app/utils/context_processors.py
def inject_cdn_url():
    """Inject CDN URL for static assets into all templates."""
    cdn_url = os.getenv("STATIC_CDN_URL", "")
    return {
        "static_cdn_url": cdn_url if cdn_url else None,
    }
```

## Troubleshooting

### Files Not Updating

**Problem**: Changes to static files not appearing in browser.

**Solution**: Invalidate CloudFront cache:

```bash
aws cloudfront create-invalidation --distribution-id <ID> --paths "/*"
```

### 404 Errors on Static Files

**Problem**: Static files return 404.

**Solution**:

1. Check files exist in S3: `aws s3 ls s3://meal-expense-tracker-dev-static/ --recursive`
2. Check S3 bucket policy allows CloudFront access
3. Check CloudFront distribution origin is correct

### CORS Issues

**Problem**: CORS errors when loading static files.

**Solution**: The S3 bucket is configured for CloudFront only (no public access). If you need CORS, add it to the bucket policy in `terraform/modules/cloudfront-static/main.tf`.

## Monitoring

Monitor CloudFront performance:

```bash
# Get distribution statistics
aws cloudfront get-distribution-config --id <DISTRIBUTION_ID>

# Monitor cache hit ratio
aws cloudwatch get-metric-statistics \
  --namespace AWS/CloudFront \
  --metric-name CacheHitRate \
  --dimensions Name=DistributionId,Value=<DISTRIBUTION_ID> \
  --start-time 2024-01-01T00:00:00Z \
  --end-time 2024-01-01T23:59:59Z \
  --period 3600 \
  --statistics Average
```

## Security

### Origin Access Control

The S3 bucket uses Origin Access Control (OAC) instead of Origin Access Identity (OAI):

- More secure and flexible
- Allows S3 GET operations from CloudFront only
- Cannot be accessed directly from internet

### HTTPS Only

CloudFront enforces HTTPS (redirect-to-https viewer protocol policy):

- All requests redirected to HTTPS
- Secure transport required

## Performance Optimization

### Cache Headers

Static files are cached for 1 year (`max-age=31536000`):

- ⚡ Faster subsequent loads
- 🔄 Requires cache invalidation for updates
- 💾 Saves CloudFront data transfer costs

### Compression

CloudFront automatically compresses responses:

- Gzip/Brotli compression enabled
- Reduces bandwidth usage
- Faster page loads

### Edge Locations

CloudFront serves from 450+ edge locations worldwide:

- ⚡ Fastest possible delivery
- 📍 Reduced latency globally
- 🌍 Better international performance

## Cost Monitoring

Monitor costs in AWS Cost Explorer:

```bash
# View S3 costs
aws ce get-cost-and-usage \
  --time-period Start=2024-01-01,End=2024-01-31 \
  --granularity MONTHLY \
  --metrics BlendedCost \
  --filter file://filters.json
```

Expected costs:

- Small traffic: ~$0.03/month
- Medium traffic: ~$0.33/month
- High traffic: ~$3.10/month

See [COST_ANALYSIS_CLOUDFRONT.md](./COST_ANALYSIS_CLOUDFRONT.md) for detailed breakdown.

## Next Steps

1. Update all templates to use `get_static_url()` where possible
2. Monitor CloudFront metrics in CloudWatch
3. Consider setting up CloudFront real-time logs
4. Monitor cache hit ratio and optimize if needed

## Additional Resources

- [AWS CloudFront Documentation](https://docs.aws.amazon.com/cloudfront/)
- [S3 Static Website Hosting](https://docs.aws.amazon.com/AmazonS3/latest/userguide/WebsiteHosting.html)
- [Origin Access Control](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/private-content-restricting-access-to-s3.html)
