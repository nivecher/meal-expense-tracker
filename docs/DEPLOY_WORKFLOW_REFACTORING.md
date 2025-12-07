# Deploy Workflow Refactoring

## Overview

This document describes the refactoring of the GitHub Actions deploy workflow to eliminate code duplication, improve maintainability, and enhance reliability.

## Problem Statement

### Before Refactoring

- **912 lines** of workflow code with ~400 lines duplicated across 4 separate deployment jobs
- **3 confusing trigger mechanisms**: `workflow_run`, `workflow_dispatch`, `repository_dispatch`
- **Rollback only worked in dev environment**
- **Linear health check backoff** (inefficient)
- **No unified error handling** across environments

### Key Issues

1. **Code Duplication**: Each environment (dev, staging, prod, staging-after-release) had nearly identical steps
2. **Maintenance Burden**: Changes required updates in multiple places
3. **Inconsistent Behavior**: Different environments had different rollback capabilities
4. **Poor Error Handling**: Limited visibility into deployment failures

## Solution

### Refactored Architecture

```
validate → build → deploy (unified) → notify
```

#### Job Structure

1. **`validate`**: Determines deployment eligibility, environment, and image tag
2. **`build`**: Builds and pushes Docker image to GHCR
3. **`deploy`**: Single unified job handling all environments
4. **`notify`**: Creates GitHub status checks

### Key Improvements

#### 1. Unified Deployment Job

- Single `deploy` job handles all environments (dev/staging/prod)
- Environment-specific behavior via inputs/outputs
- Reduced from ~900 lines to ~450 lines

#### 2. Simplified Triggers

- **Auto-deploy to dev**: `workflow_run` after successful CI on main
- **Manual deploy**: `workflow_dispatch` with environment dropdown and optional tag parameter
- **Removed**: `repository_dispatch` (redundant)

#### 3. Environment Behavior

| Environment | Trigger                    | Tag Required  | Approval    |
| ----------- | -------------------------- | ------------- | ----------- |
| Dev         | Auto (workflow_run)        | No (uses SHA) | No          |
| Staging     | Manual (workflow_dispatch) | Optional      | Optional    |
| Prod        | Manual (workflow_dispatch) | Recommended   | Recommended |

#### 4. Enhanced Error Handling

- **Exponential backoff health checks**: 15 attempts, max 60s wait
- **Automatic rollback**: Works for ALL environments using Lambda version history
- **GitHub issue creation**: Automatic issue creation on deployment failure

#### 5. Concurrency Control

- One deployment per environment at a time
- Different environments can run simultaneously
- Uses environment-specific concurrency groups

## Implementation Details

### Health Check with Exponential Backoff

```yaml
MAX_ATTEMPTS=15
for i in $(seq 1 $MAX_ATTEMPTS); do
  if curl -f -s "${DEPLOYMENT_URL}/health" > /dev/null; then
    # Success
    exit 0
  fi
  # Exponential backoff: 2^(i-1) seconds, capped at 60s
  WAIT_TIME=$((2 ** (i - 1)))
  if [ $WAIT_TIME -gt 60 ]; then
    WAIT_TIME=60
  fi
  sleep $WAIT_TIME
done
```

**Backoff Sequence**: 1s, 2s, 4s, 8s, 16s, 32s, 60s, 60s, ... (max 60s)

### Rollback Mechanism

The rollback process uses Lambda version history:

1. **Before deployment**: Capture current Lambda function configuration
2. **On failure**: Query Lambda version history to find previous version
3. **Rollback**: Update Lambda function to previous version's image URI
4. **Verify**: Health check the rolled-back deployment

**Fallback Strategy**:

- Primary: Use Lambda version history (`list-versions-by-function`)
- Fallback: Use captured current image URI from before deployment

### Image Tag Resolution

1. **Manual tag provided**: Use provided tag
2. **Git tag exists**: Use latest git tag (stripped of 'v' prefix)
3. **Fallback**: Use commit SHA (first 7 characters)

## Migration Guide

### For Developers

No changes required for normal development workflow. Dev deployments continue to auto-deploy after CI.

### For Manual Deployments

**Before**:

```yaml
# Multiple workflow_dispatch inputs, repository_dispatch events
```

**After**:

```yaml
workflow_dispatch:
  inputs:
    environment: [dev, staging, prod]
    image_tag: (optional)
```

### Breaking Changes

- **Removed**: `repository_dispatch` trigger (use `workflow_dispatch` instead)
- **Changed**: Staging/prod deployments now require explicit `workflow_dispatch` trigger

## Testing

### Manual Testing

1. **Dev auto-deploy**: Push to main, verify CI triggers deployment
2. **Manual dev deploy**: Use workflow_dispatch with environment=dev
3. **Manual staging deploy**: Use workflow_dispatch with environment=staging
4. **Rollback test**: Deploy broken version, verify rollback triggers

### Validation Checklist

- [x] Dev auto-deploys after CI success
- [x] Manual deployments work for all environments
- [x] Health checks use exponential backoff
- [x] Rollback works in all environments
- [x] GitHub issues created on failure
- [x] Status checks created correctly
- [x] Concurrency prevents duplicate deployments

## Metrics

### Code Reduction

- **Before**: 912 lines
- **After**: ~450 lines
- **Reduction**: ~50% fewer lines
- **Duplication**: Eliminated (was ~400 lines duplicated)

### Performance

- **Health check time**: Reduced from linear (up to 150s) to exponential (up to ~300s worst case, but typically much faster)
- **Deployment time**: Similar (no significant change)

## Future Improvements

1. **Blue/Green Deployments**: Implement zero-downtime deployments
2. **Canary Deployments**: Gradual rollout for production
3. **Automated Testing**: Pre-deployment smoke tests
4. **Metrics Collection**: Deployment success rate tracking
5. **Slack/Email Notifications**: Enhanced notification system

## References

- [GitHub Actions Workflow Syntax](https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions)
- [AWS Lambda Versioning](https://docs.aws.amazon.com/lambda/latest/dg/configuration-versions.html)
- [Exponential Backoff](https://en.wikipedia.org/wiki/Exponential_backoff)
