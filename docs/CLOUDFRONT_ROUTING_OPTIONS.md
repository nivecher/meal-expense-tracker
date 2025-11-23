# CloudFront Routing Options

## Current Setup (Not Configured Yet)

Currently, **all requests** including `/static/*` go through API Gateway → Lambda:

```
User Request → API Gateway → Lambda
                ↓
           /static/css/main.css → 503 Error (too large)
           /restaurants → OK (Lambda handles)
```

This is why you're seeing 503 errors on static files.

## Option 1: CloudFront in Front (Recommended)

Put CloudFront in front of everything and route intelligently:

```
User Request → CloudFront
                ↓
          /static/* → S3 (fast!)
          /(everything else) → API Gateway → Lambda
```

**Benefits:**

- ⚡ Static files from CDN edge locations
- ✅ Eliminates 503 errors
- 💰 Reduced Lambda invocations
- 🚀 Better performance overall

**Implementation:** Need to modify API Gateway module to use CloudFront as origin

## Option 2: Direct CDN URLs (Current Implementation)

Keep API Gateway as-is, but templates generate CloudFront URLs:

```
User visits meals.dev.nivecher.com → API Gateway (HTML page)
HTML contains: <link href="https://d123.cloudfront.net/css/main.css">
Browser requests: https://d123.cloudfront.net/css/main.css → CloudFront
API requests: meals.dev.nivecher.com/api/* → API Gateway → Lambda
```

**Benefits:**

- ✅ Backward compatible
- ✅ No infrastructure changes
- ✅ Easy to roll out gradually

**Limitation:**

- Still need to handle direct `/static/*` requests (fallback to Lambda or error)

## Recommended: Hybrid Approach

Implement Option 1 with CloudFront routing:

1. **CloudFront as main entry point** (`meals.dev.nivecher.com`)
2. **Origin for `/static/*`**: S3 bucket
3. **Origin for `/` and other routes**: API Gateway

This gives you:

- Fast static files from edge
- Lambda only handles API/dynamic content
- Single domain for all traffic
- Professional CDN architecture

Would you like me to implement the CloudFront routing approach (Option 1)?
