# Supabase Migration Guide

## Quick Start: 3 Steps to Save $75/month

### Step 1: Create Supabase Project (5 minutes)

1. Go to [supabase.com](https://supabase.com)
2. Sign up (free)
3. Create new project
4. Wait for database to provision (~2 minutes)
5. Get your connection string:
   - Go to Project Settings → Database
   - Copy the "Connection string" (URI format)
   - Example: `postgresql://postgres:[PASSWORD]@db.xxxxx.supabase.co:5432/postgres`

### Step 2: Add Connection to AWS Secrets Manager (2 minutes)

```bash
# Create Supabase secret in AWS
aws secretsmanager create-secret \
  --name meal-expense-tracker/dev/supabase-connection \
  --secret-string "postgresql+pg8000://postgres:[YOUR_PASSWORD]@db.[YOUR_PROJECT].supabase.co:5432/postgres" \
  --kms-key-id alias/meal-expense-tracker-dev-main
```

### Step 3: Update Lambda to Use Supabase (Already Done!)

The code already supports this - just need to:

1. Set `DATABASE_URL` to Supabase connection string
2. Remove VPC from Lambda (no longer needed!)
3. Deploy

---

## Migration Steps

### 1. Get Your Supabase Connection String

After creating your Supabase project, you'll have a connection string like:

```
postgresql://postgres.xxxxx:[PASSWORD]@aws-0-us-east-1.pooler.supabase.com:6543/postgres
```

**Important**: Use the `pooler` endpoint for better connection pooling.

### 2. Store in AWS Secrets Manager

Store it as a secret:

```bash
aws secretsmanager create-secret \
  --name meal-expense-tracker/dev/supabase-connection \
  --description "Supabase PostgreSQL connection string" \
  --secret-string "postgresql+pg8000://postgres.[PROJECT]:[PASSWORD]@aws-0-us-east-1.pooler.supabase.com:6543/postgres" \
  --kms-key-id alias/meal-expense-tracker-dev-main
```

### 3. Update Lambda Configuration

The Lambda already reads from `DATABASE_URL`. We just need to update it to point to Supabase.

### 4. Run Migrations Against Supabase

```bash
# Export connection string
export DATABASE_URL="postgresql+pg8000://postgres.[PROJECT]:[PASSWORD]@aws-0-us-east-1.pooler.supabase.com:6543/postgres"

# Run migrations
cd /home/mtd37/workspace/meal-expense-tracker
flask db upgrade
```

### 5. Update Terraform to Remove Aurora/RDS Proxy

We'll update Terraform to remove expensive components.

### 6. Remove Lambda from VPC

Since Lambda no longer needs to connect to VPC resources, we can remove it from VPC entirely.

---

## Expected Cost Savings

| Component            | Before  | After  | Savings       |
| -------------------- | ------- | ------ | ------------- |
| Aurora Serverless v2 | $45     | $0     | $45           |
| RDS Proxy            | $20     | $0     | $20           |
| VPC ENI (Lambda)     | $30     | $0     | $30           |
| Supabase Free Tier   | $0      | $0     | $0            |
| **Total**            | **$95** | **$0** | **$75/month** |

Supabase free tier includes:

- 500MB database
- 50K monthly active users
- 2GB file storage

---

## Connection String Format

Use this format for Supabase:

```
postgresql+pg8000://postgres.[PROJECT_REF]:[PASSWORD]@aws-0-us-east-1.pooler.supabase.com:6543/postgres
```

The `+pg8000` driver is already configured in your code!

---

## Next Steps

1. Create Supabase account and get connection string
2. I'll update the Lambda configuration
3. Run migrations against Supabase
4. Deploy the updated Lambda
5. Remove Aurora/RDS Proxy from Terraform
