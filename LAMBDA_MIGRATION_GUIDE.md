# Lambda Migration Strategy Guide

This guide explains the recommended approach for handling database migrations in Lambda deployments to prevent data loss and ensure reliable schema changes.

## 🎯 Migration Strategy Overview

### **Automated Migration Approach**

- **Auto-migration on first request**: Migrations run automatically when Lambda starts
- **Safe migration history repair**: Automatically fixes missing migration history
- **Data preservation**: All existing data is preserved during schema changes
- **Environment-aware**: Different behavior for development vs production

### **Manual Migration Options**

- **Remote admin commands**: Use `remote_admin.py` for controlled migrations
- **Direct Lambda invocation**: Call migration operations directly
- **Emergency fixes**: Scripts for fixing migration history

## 🚀 Automatic Migration Setup

### 1. Enable Auto-Migration

Set the environment variable in your Lambda configuration:

```bash
# Enable auto-migration
AUTO_MIGRATE=true

# Optional: Set environment
FLASK_ENV=production
```

### 2. How Auto-Migration Works

The migration manager automatically:

1. **Checks database state** on first Lambda request
2. **Detects missing migration history** and fixes it
3. **Runs pending migrations** safely
4. **Logs all operations** for monitoring
5. **Only runs once per Lambda container** (performance optimization)

### 3. Migration States Handled

| State                              | Description                         | Action                         |
| ---------------------------------- | ----------------------------------- | ------------------------------ |
| `empty`                            | No tables exist                     | Run initial migration          |
| `tables_without_migration_history` | Tables exist but no alembic_version | Fix history, then migrate      |
| `pending_migrations`               | Tables exist, migrations pending    | Run pending migrations         |
| `up_to_date`                       | Everything current                  | No action needed               |
| `inconsistent`                     | Migration history corrupted         | Log warning, manual fix needed |

## 🛠️ Manual Migration Commands

### Remote Admin Commands

```bash
# Check migration status
python scripts/remote_admin.py run-migrations --dry-run

# Run migrations normally
python scripts/remote_admin.py --confirm run-migrations

# Fix migration history for existing tables
python scripts/remote_admin.py --confirm run-migrations --fix-history

# Run to specific revision
python scripts/remote_admin.py --confirm run-migrations --target-revision abc123
```

### Direct Lambda Invocation

```bash
# Check migration state
aws lambda invoke \
  --function-name your-function-name \
  --payload '{"admin_operation": "run_migrations", "parameters": {"dry_run": true}}' \
  response.json

# Run migrations
aws lambda invoke \
  --function-name your-function-name \
  --payload '{"admin_operation": "run_migrations", "parameters": {}, "confirm": true}' \
  response.json
```

## 🔧 Emergency Migration Fixes

### Fix Migration History Script

If you encounter "already exists" errors:

```bash
# Run the fix script
python scripts/fix_rds_migration.py

# Or use remote admin
python scripts/remote_admin.py --confirm run-migrations --fix-history
```

### Manual Database Fix

If scripts don't work, connect directly to RDS:

```sql
-- Create alembic_version table if missing
CREATE TABLE IF NOT EXISTS alembic_version (
    version_num VARCHAR(32) NOT NULL,
    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);

-- Set to latest revision (replace with actual revision)
INSERT INTO alembic_version (version_num) VALUES ('your_latest_revision');
```

## 📋 Deployment Checklist

### Before Deployment

- [ ] **Test migrations locally**: `flask db upgrade`
- [ ] **Check migration files**: Ensure all migrations are committed
- [ ] **Backup database**: Create RDS snapshot
- [ ] **Review schema changes**: Ensure no destructive operations

### During Deployment

- [ ] **Set AUTO_MIGRATE=true**: Enable automatic migrations
- [ ] **Monitor Lambda logs**: Watch for migration messages
- [ ] **Check migration status**: Use dry-run to verify
- [ ] **Test application**: Ensure everything works after migration

### After Deployment

- [ ] **Verify data integrity**: Check that all data is preserved
- [ ] **Monitor performance**: Ensure migrations don't impact performance
- [ ] **Update documentation**: Document any schema changes
- [ ] **Clean up**: Remove old migration files if needed

## 🚨 Troubleshooting

### Common Issues

#### 1. "Table already exists" Error

**Cause**: Database has tables but no migration history

**Solution**:

```bash
# Use fix-history option
python scripts/remote_admin.py --confirm run-migrations --fix-history

# Or run fix script
python scripts/fix_rds_migration.py
```

#### 2. Migration Fails During Lambda Startup

**Cause**: Migration errors prevent Lambda from starting

**Solution**:

1. Disable auto-migration temporarily: `AUTO_MIGRATE=false`
2. Fix migration issues manually
3. Re-enable auto-migration: `AUTO_MIGRATE=true`

#### 3. Performance Issues

**Cause**: Migrations running on every request

**Solution**:

- Auto-migration only runs once per Lambda container
- Check logs to ensure it's not running repeatedly
- Use dry-run to check migration status

#### 4. Data Loss Concerns

**Cause**: Worried about losing data during migrations

**Solution**:

- Always backup before migrations
- Test migrations on staging environment
- Use `--dry-run` to preview changes
- Review migration files for destructive operations

## 🔒 Security Considerations

### Environment Variables

```bash
# Required for auto-migration
AUTO_MIGRATE=true

# Optional: Control migration behavior
FLASK_ENV=production
MIGRATION_TIMEOUT=300  # 5 minutes
```

### IAM Permissions

Ensure Lambda has these permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["rds:DescribeDBInstances", "rds:DescribeDBClusters"],
      "Resource": "*"
    }
  ]
}
```

## 📊 Monitoring and Logging

### Migration Logs

The migration manager logs all operations:

```
INFO - Auto-migration: Database is up to date
INFO - Migration state: pending_migrations
INFO - Running 2 pending migrations...
INFO - Database migrations completed successfully. Revision: abc123 → def456
```

### CloudWatch Metrics

Monitor these metrics:

- **Migration duration**: Time taken for migrations
- **Migration success rate**: Percentage of successful migrations
- **Lambda cold starts**: Impact of migrations on startup time

### Alerts

Set up CloudWatch alarms for:

- Migration failures
- Long migration times (>5 minutes)
- Database connection errors

## 🎯 Best Practices

### 1. **Always Test Locally First**

```bash
flask db upgrade
flask db downgrade base
flask db upgrade
```

### 2. **Use Dry-Run Before Production**

```bash
python scripts/remote_admin.py run-migrations --dry-run
```

### 3. **Backup Before Major Changes**

```bash
# Create RDS snapshot
aws rds create-db-snapshot \
  --db-instance-identifier your-db \
  --db-snapshot-identifier pre-migration-backup
```

### 4. **Monitor Migration Progress**

- Watch CloudWatch logs during deployment
- Check migration status after deployment
- Verify data integrity

### 5. **Use Environment-Specific Settings**

```bash
# Development: Always run migrations
AUTO_MIGRATE=true
FLASK_ENV=development

# Production: Enable with caution
AUTO_MIGRATE=true
FLASK_ENV=production
```

## 🔄 Migration Workflow

### Standard Deployment Workflow

1. **Develop and test locally**

   ```bash
   flask db migrate -m "Add new feature"
   flask db upgrade
   ```

2. **Commit and push changes**

   ```bash
   git add migrations/
   git commit -m "Add migration for new feature"
   git push
   ```

3. **Deploy to staging**

   ```bash
   # Deploy with auto-migration enabled
   terraform apply
   ```

4. **Verify staging**

   ```bash
   python scripts/remote_admin.py run-migrations --dry-run
   ```

5. **Deploy to production**

   ```bash
   # Deploy with auto-migration enabled
   terraform apply
   ```

6. **Monitor and verify**
   ```bash
   # Check migration status
   python scripts/remote_admin.py run-migrations --dry-run
   ```

This approach ensures safe, automated migrations while preserving all data and providing manual control when needed.
