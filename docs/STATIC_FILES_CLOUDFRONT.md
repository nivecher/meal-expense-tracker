# Static Files via CloudFront + S3

## Architecture

```
User Request
    ↓
Route53 DNS → CloudFront Distribution
    ↓
    ├─ /static/css/file.css → S3 Bucket (cached, fast!)
    └─ /restaurants, /api/* → API Gateway → Lambda (dynamic)
```

## Key Points

✅ **CloudFront is the entry point** - All traffic goes through CloudFront  
✅ **Static files routed to S3** - `/static/*` patterns served from S3 edge locations  
✅ **Dynamic content routed to Lambda** - Everything else goes to API Gateway  
✅ **Python code is transparent** - Uses standard `url_for('static', ...)`  
✅ **Smaller Lambda package** - Static files excluded from Docker image  
✅ **DNS points to CloudFront** - Single domain, smart routing

## Deploying

### 1. Deploy Infrastructure

```bash
cd terraform
terraform init
terraform plan
terraform apply
```

This creates:

- S3 bucket for static files
- CloudFront distribution with dual origins
- Route53 record pointing to CloudFront
- Smart cache behaviors

### 2. Sync Static Files to S3

```bash
./scripts/sync_static_to_s3.sh
```

This uploads:

- CSS files → S3 (`/static/css/*`)
- JS files → S3 (`/static/js/*`)
- Images → S3 (`/static/img/*`)
- Other static assets

### 3. Deploy Lambda (without static files)

```bash
./scripts/deploy_with_migrations.sh -e dev
```

The Lambda image now excludes `/app/static/` directory, making it smaller and faster.

## How It Works

### Request Flow

1. **User visits**: `https://meals.dev.nivecher.com/restaurants`

   - Route53 resolves to CloudFront
   - CloudFront checks path: `/restaurants` doesn't match `/static/*`
   - Routes to API Gateway origin
   - API Gateway invokes Lambda
   - Lambda renders HTML with static file links

2. **Browser loads**: HTML contains `<link href="/static/css/main.css">`
   - Browser requests: `https://meals.dev.nivecher.com/static/css/main.css`
   - Route53 resolves to CloudFront
   - CloudFront checks path: `/static/css/main.css` matches `/static/*`
   - Routes to S3 origin (served from edge location)
   - Fast response, cached globally

### Cache Behavior

- **Static files** (`/static/*`): Cached for 1 year at CloudFront edge
- **Dynamic content** (`/*`): Not cached, always fresh

### Performance

- ⚡ Static files: 50-90% faster (served from CDN edge)
- 📦 Lambda package: 30-50% smaller (no static files)
- 🚀 Cold starts: Faster (smaller Lambda package)
- 💰 Cost: ~$0.30/month for CloudFront (worth it!)

## Troubleshooting

### Static files not loading

1. Check files are in S3:

   ```bash
   aws s3 ls s3://meal-expense-tracker-dev-static/ --recursive
   ```

2. Check CloudFront distribution:

   ```bash
   cd terraform
   terraform output cloudfront_distribution_id
   ```

3. Invalidate cache if needed:
   ```bash
   aws cloudfront create-invalidation --distribution-id <ID> --paths "/*"
   ```

### Lambda can't find static files

This is expected! Static files are not in Lambda anymore. They're served by CloudFront from S3.

If you see 404 errors, check:

- Are files uploaded to S3?
- Is CloudFront configured correctly?
- Are the cache behaviors set up properly?

## Benefits

### Performance

- ✅ Eliminates 503 errors (static files too large for Lambda)
- ✅ Faster load times (CDN edge locations)
- ✅ Better cache hit rates
- ✅ Reduced Lambda memory usage

### Cost

- 💰 CloudFront: ~$0.30/month
- 💰 Smaller Lambda: Lower execution costs
- 💰 Fewer Lambda invocations for static files

### Developer Experience

- ✅ Simpler Python code (no CDN awareness)
- ✅ Standard Flask patterns (`url_for('static', ...)`)
- ✅ Smaller deployments
- ✅ Faster CI/CD

## Files Changed

### Excluded from Lambda

- `app/static/css/*` → S3
- `app/static/js/*` → S3
- `app/static/img/*` → S3
- `app/static/data/*` → S3

### Still in Lambda

- Python application code
- Templates (HTML, Jinja2)
- Migrations
- Configuration files

## Next Steps

1. ✅ Deploy infrastructure: `cd terraform && terraform apply`
2. ✅ Sync static files: `./scripts/sync_static_to_s3.sh`
3. ✅ Deploy Lambda: `./scripts/deploy_with_migrations.sh`
4. ✅ Test: Visit application and check Network tab in DevTools
5. ⏳ Verify: Static files should load from `cloudfront.net` domain

## Monitoring

Check CloudFront metrics:

```bash
aws cloudwatch get-metric-statistics \
  --namespace AWS/CloudFront \
  --metric-name CacheHitRate \
  --dimensions Name=DistributionId,Value=<ID> \
  --start-time 2024-01-01T00:00:00Z \
  --end-time 2024-01-01T23:59:59Z \
  --period 3600 \
  --statistics Average
```

Expected: Cache hit rate > 90% for static files.
