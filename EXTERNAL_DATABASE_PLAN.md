# External Database Plan (Neon/Supabase)

## Architecture Overview

```
┌─────────────────────────────────────────────────────┐
│         Your AWS Infrastructure                      │
│                                                      │
│  ┌─────────────┐                                     │
│  │   Lambda    │  (No VPC needed!)                   │
│  └──────┬──────┘                                     │
│         │ HTTPS                                      │
│         │ over Internet                              │
│         ▼                                            │
│  ┌──────────────────────────────────────┐           │
│  │  External Service (Neon or Supabase) │           │
│  │  - Managed Postgres                   │           │
│  │  - Free tier                          │           │
│  │  - Auto-scaling                       │           │
│  └──────────────────────────────────────┘           │
└─────────────────────────────────────────────────────┘
```

## Connection Flow

1. **Lambda wakes up** (no VPC, no ENI cost!)
2. **Gets connection string** from AWS Secrets Manager
3. **Connects via HTTPS** to external database
4. **Queries database** just like any HTTPS API
5. **Returns data** to user

## No AWS Resources Needed

Since Lambda connects via HTTPS over the internet, you need:

- ❌ No VPC
- ❌ No RDS Proxy
- ❌ No Aurora
- ❌ No database subnet groups
- ❌ No NAT Gateway
- ✅ Just Lambda + API Gateway (FREE tier)

## Cost Savings Breakdown

| Component                 | Current Cost  | With External DB |
| ------------------------- | ------------- | ---------------- |
| Aurora Serverless v2      | $45/month     | $0               |
| RDS Proxy                 | $20/month     | $0               |
| VPC ENI (Lambda)          | $30/month     | $0               |
| Neon/Supabase (free tier) | $0            | $0               |
| **Total**                 | **$95/month** | **$0/month**     |
| **Savings**               |               | **$95/month**    |

## Free Tier Limits

Both Neon and Supabase offer generous free tiers:

- **Neon**: 0.5 GB storage, unlimited compute hours
- **Supabase**: 500 MB database, 50K monthly active users

For a meal expense tracker, this is more than enough!

## Implementation Steps

1. Create account at neon.tech or supabase.com
2. Create a PostgreSQL database
3. Get connection string
4. Store it in AWS Secrets Manager
5. Update Lambda to read from new secret
6. Remove Lambda from VPC in Terraform
7. Destroy Aurora/RDS Proxy in Terraform
8. **Save $95/month forever**

## Deployment Location

- **Neon**: Runs on Vercel's cloud infrastructure
- **Supabase**: Runs on AWS behind the scenes (but you don't manage it)

You access them via HTTPS from your Lambda, just like any API call.

## Why This Works

Traditional setup:

- Lambda in VPC → RDS Proxy → Aurora (all in AWS)

New setup:

- Lambda (no VPC) → HTTPS → External Database

The external database handles:

- Scaling
- Backups
- Security
- Connection pooling

You just connect to it like any HTTPS endpoint!
