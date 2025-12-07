# Deployment Quick Reference

## Quick Start

### Auto-Deploy to Dev

**Trigger**: Automatic after CI succeeds on `main` branch

**No action required** - deployment happens automatically.

### Manual Deploy

1. Go to **Actions** → **Deploy** workflow
2. Click **Run workflow**
3. Select:
   - **Environment**: `dev`, `staging`, or `prod`
   - **Image tag** (optional): Specific version/tag to deploy
4. Click **Run workflow**

## Workflow Structure

```
validate → build → deploy → notify
```

- **validate**: Checks CI status, determines environment and tag
- **build**: Builds Docker image and pushes to GHCR
- **deploy**: Deploys to AWS (Terraform, ECR, Lambda, health checks)
- **notify**: Creates GitHub status checks

## Environment Behavior

| Environment | Trigger             | Tag         | Approval    | Auto-Deploy |
| ----------- | ------------------- | ----------- | ----------- | ----------- |
| **dev**     | Auto (CI) or Manual | SHA         | No          | ✅ Yes      |
| **staging** | Manual only         | Optional    | Optional    | ❌ No       |
| **prod**    | Manual only         | Recommended | Recommended | ❌ No       |

## Health Checks

**Strategy**: Exponential backoff

- **Attempts**: 15 maximum
- **Wait times**: 1s, 2s, 4s, 8s, 16s, 32s, 60s (max)
- **Total time**: Up to ~15 minutes (worst case)

## Rollback

**Automatic rollback** triggers when:

- Health check fails after all retries
- Previous Lambda version is available

**Process**:

1. Query Lambda version history
2. Get previous version's image URI
3. Update Lambda to previous version
4. Verify rollback with health check
5. Create GitHub issue

## Common Tasks

### Deploy Specific Version to Staging

```yaml
workflow_dispatch:
  environment: staging
  image_tag: v1.2.3
```

### Check Deployment Status

1. Go to **Actions** → **Deploy** workflow
2. Find the latest run
3. Check job status:
   - ✅ Green: Success
   - ⚠️ Yellow: Rolled back
   - ❌ Red: Failed

### View Deployment Logs

1. Go to **Actions** → **Deploy** workflow
2. Click on the workflow run
3. Expand job steps to view logs

### Manual Rollback

If automatic rollback fails:

```bash
# Get previous Lambda version
aws lambda list-versions-by-function \
  --function-name meal-expense-tracker-<env>

# Get previous image URI
aws lambda get-function \
  --function-name meal-expense-tracker-<env> \
  --qualifier <previous_version>

# Update Lambda
aws lambda update-function-code \
  --function-name meal-expense-tracker-<env> \
  --image-uri <previous_image_uri>
```

## Troubleshooting

### Health Check Failing

**Symptoms**: Deployment fails at "Verify Deployment" step

**Check**:

1. Application logs in CloudWatch
2. API Gateway configuration
3. Lambda function status
4. Network connectivity

**Commands**:

```bash
# Check Lambda status
aws lambda get-function --function-name meal-expense-tracker-dev

# Manual health check
curl https://meals.dev.nivecher.com/health

# Check API Gateway
aws apigatewayv2 get-apis --query "Items[?contains(Name, 'meal-expense-tracker-dev')]"
```

### Rollback Not Working

**Symptoms**: Deployment fails but rollback doesn't trigger

**Check**:

1. Lambda version history exists
2. Previous version available
3. ECR image exists
4. AWS permissions

**Commands**:

```bash
# List Lambda versions
aws lambda list-versions-by-function \
  --function-name meal-expense-tracker-dev

# Check ECR images
aws ecr list-images \
  --repository-name meal-expense-tracker-dev-lambda
```

### Build Failing

**Symptoms**: Build job fails

**Check**:

1. Docker build logs
2. Dependencies in `requirements.txt`
3. GHCR permissions
4. GitHub Actions limits

### Terraform Errors

**Symptoms**: Infrastructure deployment fails

**Check**:

1. Terraform plan output
2. AWS permissions
3. Backend configuration
4. State file conflicts

**Commands**:

```bash
# Check Terraform state
cd terraform/environments/dev
terraform show

# Validate Terraform
terraform validate
```

## Deployment URLs

| Environment | URL                                  |
| ----------- | ------------------------------------ |
| **dev**     | <https://meals.dev.nivecher.com>     |
| **staging** | <https://meals.staging.nivecher.com> |
| **prod**    | <https://meals.nivecher.com>         |

## Image Tags

**Tag Resolution Order**:

1. Manual tag (if provided)
2. Latest git tag (stripped of 'v')
3. Commit SHA (first 7 characters)

**Examples**:

- `v1.2.3` → `1.2.3`
- `dev` → `dev`
- `abc1234` → `abc1234` (SHA)

## Concurrency

**Behavior**:

- One deployment per environment at a time
- Different environments can run simultaneously
- Queued deployments wait (don't cancel in-progress)

**Example**:

- Dev deployment running → New dev deployment queued ⏳
- Dev deployment running → Staging deployment runs in parallel ✅

## GitHub Issues

**Automatic Issues Created**:

- On deployment failure
- Includes: environment, version, commit, workflow link
- Labels: `deployment`, `rollback`, `urgent`, `<environment>`

**Issue Template**:

```
🚨 Deployment Failed - <env> (<version>)

## Deployment Verification Failed

- Environment: <env>
- Version: <version>
- Commit: <sha>
- Workflow: [View Run](<url>)
- Rollback: ✅/❌
```

## Best Practices

### Before Deploying

- [ ] Run tests locally
- [ ] Review changes
- [ ] Check CI status
- [ ] Verify dependencies

### For Production

- [ ] Use version tags (not SHA)
- [ ] Review deployment plan
- [ ] Have rollback plan ready
- [ ] Monitor after deployment

### After Deployment

- [ ] Verify health endpoint
- [ ] Check application logs
- [ ] Monitor error rates
- [ ] Test critical paths

## Emergency Procedures

### Immediate Rollback

1. Go to **Actions** → **Deploy** workflow
2. Find failed deployment
3. Check if automatic rollback succeeded
4. If not, use manual rollback commands (see above)

### Disable Auto-Deploy

Temporarily disable auto-deploy by modifying workflow:

```yaml
# Comment out workflow_run trigger
# workflow_run:
#   workflows: [CI]
#   types:
#     - completed
#   branches: [main]
```

### Force Deployment

If deployment is stuck:

1. Cancel workflow run
2. Wait for concurrency lock to release
3. Retry deployment

## Support

**Documentation**:

- [Deploy Workflow Refactoring](./DEPLOY_WORKFLOW_REFACTORING.md)
- [Deploy Architecture](./DEPLOY_ARCHITECTURE.md)

**Resources**:

- GitHub Actions logs
- AWS CloudWatch logs
- Terraform state
- Lambda function logs

## Quick Commands Cheat Sheet

```bash
# Check deployment status
gh run list --workflow=deploy.yml

# View latest deployment logs
gh run view --log --workflow=deploy.yml

# Check Lambda function
aws lambda get-function --function-name meal-expense-tracker-dev

# Health check
curl https://meals.dev.nivecher.com/health

# List Lambda versions
aws lambda list-versions-by-function --function-name meal-expense-tracker-dev

# Check ECR images
aws ecr list-images --repository-name meal-expense-tracker-dev-lambda

# View CloudWatch logs
aws logs tail /aws/lambda/meal-expense-tracker-dev --follow
```
