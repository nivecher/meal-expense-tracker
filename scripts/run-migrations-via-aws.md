# Running Database Migrations via AWS

Since your local WSL environment can't reach Supabase, here are alternatives:

## Option 1: Use AWS CloudShell (Recommended)

AWS CloudShell is a browser-based terminal that has AWS CLI and network access.

### Steps:

1. Go to AWS Console → CloudShell
2. Clone your repository
3. Run migrations from there

```bash
# In AWS CloudShell
git clone <your-repo-url>
cd meal-expense-tracker

# Choose environment (dev|staging|prod)
ENV=staging

aws secretsmanager get-secret-value \
  --secret-id meal-expense-tracker/${ENV}/supabase-connection \
  --region us-east-1 \
  --query SecretString \
  --output text | sed 's/^/export DATABASE_URL=/' | bash

# Set up Python environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run migrations
flask db upgrade
```

## Option 2: Run Migrations Locally (if you fix network)

The error shows Supabase is trying to connect via IPv6. To force IPv4:

```bash
# Get the connection string
ENV=staging
CONN=$(aws secretsmanager get-secret-value \
  --secret-id meal-expense-tracker/${ENV}/supabase-connection \
  --region us-east-1 \
  --query SecretString \
  --output text)

# Force IPv4 by removing any IPv6 hostname
CONN_IPV4=$(echo $CONN | sed 's/@db\./@' | echo "postgresql+pg8000://postgres:9CjYiHlWnllbBJ6X@db.gtnhucaocpjytmrbesss.supabase.co:5432/postgres")

export DATABASE_URL="$CONN_IPV4"
flask db upgrade
```

## Option 3: Manually Create Tables

If migrations are too difficult, you can create tables directly in Supabase:

1. Go to Supabase Dashboard
2. Go to SQL Editor
3. Run your migrations manually
