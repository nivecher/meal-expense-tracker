# DynamoDB Migration Plan

## Current Cost Analysis

| Component            | Current Cost  | With DynamoDB    |
| -------------------- | ------------- | ---------------- |
| Aurora Serverless v2 | $45/month     | $0               |
| RDS Proxy            | $20/month     | $0               |
| VPC ENI (Lambda)     | $30/month     | $0               |
| DynamoDB (estimated) | $0            | $5-10/month      |
| **Total**            | **$95/month** | **$5-10/month**  |
| **Savings**          |               | **$85-90/month** |

## Migration Complexity: HIGH ⚠️

Switching from SQL to DynamoDB requires:

1. Rewrite all models (User, Expense, Restaurant, Category, Tag)
2. Rewrite all queries (DynamoDB SDK vs SQLAlchemy)
3. Remove Flask-SQLAlchemy entirely
4. Implement single-table design or multiple tables
5. Rewrite migrations system
6. Update all views/forms that depend on SQL queries

**Estimated time: 3-5 days**

## Alternative: Keep Current Setup + Optimize

Instead of full DynamoDB rewrite, you could:

### Option A: Neon Serverless Postgres (EASIEST)

- Similar to Postgres you're using now
- **Zero infrastructure cost** (free tier)
- Just change connection string
- **15 minutes to implement**
- Save: $95/month

### Option B: Supabase (ALSO EASY)

- Managed Postgres with HTTP API
- **Zero infrastructure cost** (free tier)
- Just change connection string
- **15 minutes to implement**
- Save: $95/month

### Option C: DynamoDB (HARD)

- Complete rewrite of data layer
- **3-5 days of development**
- Requires changing every model, query, form
- Save: $85-90/month (same as Postgres options)

## Recommendation

**Go with Neon or Supabase** - you get the same $95/month savings with 15 minutes of work vs 3-5 days of work!

The SQL → DynamoDB migration is a major architectural change that will take days. The Postgres alternatives give you the same cost savings immediately.
