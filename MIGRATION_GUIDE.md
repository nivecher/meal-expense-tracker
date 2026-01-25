# Database Migration Guide

This guide explains how to handle database migrations for the Meal Expense Tracker application, both locally and remotely.

## Local Migrations

### Normal Migration Process

1. **Create a new migration:**

   ```bash
   flask db migrate -m "Description of changes"
   ```

2. **Apply migrations:**

   ```bash
   flask db upgrade
   ```

3. **Check migration status:**
   ```bash
   flask db current
   flask db history
   ```

### Handling "Already Exists" Errors

If you get errors like `relation "user" already exists`, it means your database has tables but no migration history. Here's how to fix it:

1. **Option 1: Reset and recreate (DESTROYS DATA)**

   ```bash
   flask db downgrade base
   flask db upgrade
   ```

2. **Option 2: Fix migration history (PRESERVES DATA)**
   ```bash
   python scripts/fix_migration_history.py
   flask db upgrade
   ```

## Remote Migrations (RDS via Lambda)

### Normal Remote Migration Process

1. **Check what would be migrated:**

   ```bash
   python scripts/remote_admin.py run-migrations --dry-run
   ```

2. **Run migrations:**
   ```bash
   python scripts/remote_admin.py --confirm run-migrations
   ```

### Handling Remote "Already Exists" Errors

If you get `relation "user" already exists` errors remotely, use the fix-history option:

```bash
python scripts/remote_admin.py --confirm run-migrations --fix-history
```

This will:

1. Create the `alembic_version` table if it doesn't exist
2. Set the current revision to the latest migration
3. Allow future migrations to run normally

### Migration Commands Reference

| Command                                   | Description                                 |
| ----------------------------------------- | ------------------------------------------- |
| `run-migrations --dry-run`                | Show what would be migrated without running |
| `run-migrations`                          | Run all pending migrations                  |
| `run-migrations --fix-history`            | Fix migration history for existing tables   |
| `run-migrations --target-revision abc123` | Run to specific revision                    |

## Troubleshooting

### Common Issues

1. **"Table already exists" error**

   - **Cause**: Database has tables but no migration history
   - **Solution**: Use `--fix-history` option or run `fix_migration_history.py` locally

2. **"No migration history found"**

   - **Cause**: No migration files exist
   - **Solution**: Create initial migration with `flask db init` and `flask db migrate`

3. **"Migration failed"**
   - **Cause**: Database schema conflicts
   - **Solution**: Check migration files and database state

### Best Practices

1. **Always test locally first**

   ```bash
   flask db upgrade
   ```

2. **Use dry-run before remote migrations**

   ```bash
   python scripts/remote_admin.py run-migrations --dry-run
   ```

3. **Backup before major migrations**

   - For RDS: Use AWS RDS snapshots
   - For local: Copy database file

4. **Check migration status regularly**

   ```bash
   flask db current
   python scripts/remote_admin.py run-migrations --dry-run
   ```

5. **Enable RLS for new public tables**

   Any new table in the `public` schema should have RLS enabled and explicit
   policies added in the same migration. This keeps Supabase security advisors
   clean and prevents unintended data exposure.

## Migration Files

- **Local migrations**: `migrations/versions/`
- **Migration script**: `migrate_db.py`
- **Fix script**: `scripts/fix_migration_history.py`
- **Remote admin**: `scripts/remote_admin.py`

## Database States

| State                      | Description                               | Solution               |
| -------------------------- | ----------------------------------------- | ---------------------- |
| **Empty**                  | No tables, no migration history           | Run `flask db upgrade` |
| **Normal**                 | Tables exist, migration history exists    | Run `flask db upgrade` |
| **Tables without history** | Tables exist, no migration history        | Use `--fix-history`    |
| **Inconsistent**           | Migration history exists but is corrupted | Reset and recreate     |

## Security Notes

- Remote migrations require AWS credentials with Lambda invoke permissions
- Always use `--confirm` for destructive operations
- Test migrations on staging environment first
- Keep migration files in version control
