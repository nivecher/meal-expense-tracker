# Deployment Architecture

## Overview

This document describes the architecture and design decisions for the unified deployment workflow.

## Architecture Diagram

```
┌─────────────────┐
│   CI Workflow   │
│   (on main)     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  workflow_run   │
│   trigger       │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────────────────┐
│              Deploy Workflow                    │
│                                                 │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐ │
│  │ validate │───▶│  build   │───▶│  deploy  │ │
│  └──────────┘    └──────────┘    └────┬─────┘ │
│                                         │       │
│                                         ▼       │
│                                    ┌──────────┐ │
│                                    │  notify  │ │
│                                    └──────────┘ │
└─────────────────────────────────────────────────┘
```

## Workflow Stages

### 1. Validate Stage

**Purpose**: Determine deployment eligibility and parameters

**Responsibilities**:

- Check CI workflow status (for `workflow_run` triggers)
- Determine target environment
- Resolve image tag/version

**Outputs**:

- `should_deploy`: Boolean indicating if deployment should proceed
- `environment`: Target environment (dev/staging/prod)
- `image_tag`: Docker image tag to deploy
- `version`: Version string
- `tag`: Git tag (if available)

**Logic**:

```yaml
if workflow_run: environment = dev
  should_deploy = CI succeeded
else if workflow_dispatch: environment = user input
  should_deploy = true
```

### 2. Build Stage

**Purpose**: Build and push Docker image to GitHub Container Registry

**Responsibilities**:

- Set up build environment
- Build Docker image
- Tag image appropriately
- Push to GHCR

**Image Tags**:

- Version tag (from validate)
- `latest` (if on main branch)
- SHA tag (short commit hash)

**Dependencies**: `validate` job

### 3. Deploy Stage

**Purpose**: Deploy application to target environment

**Responsibilities**:

- Deploy infrastructure (Terraform)
- Push image to ECR
- Update Lambda function
- Sync static files to S3
- Verify deployment (health checks)
- Rollback on failure

**Sub-stages**:

#### 3.1 Infrastructure Deployment

- Generate Terraform backend configs
- Initialize Terraform
- Plan and apply changes

#### 3.2 Container Deployment

- Get ECR repository URI
- Pull image from GHCR
- Tag and push to ECR
- Update Lambda function code

#### 3.3 Static Assets

- Sync static files to S3 bucket

#### 3.4 Verification

- Health check with exponential backoff
- Rollback on failure

**Dependencies**: `validate`, `build` jobs

### 4. Notify Stage

**Purpose**: Report deployment status

**Responsibilities**:

- Create GitHub status checks
- Report deployment outcome

**Dependencies**: `validate`, `deploy` jobs

## Environment Configuration

### Dev Environment

**Characteristics**:

- Auto-deploys after CI success
- Uses commit SHA as image tag
- No approval required
- Fast feedback loop

**Deployment Flow**:

```
CI Success → workflow_run → validate → build → deploy → notify
```

### Staging Environment

**Characteristics**:

- Manual trigger required
- Optional tag parameter
- Optional approval (via GitHub environment protection)
- Pre-production testing

**Deployment Flow**:

```
Manual Trigger → validate → build → deploy → notify
```

### Production Environment

**Characteristics**:

- Manual trigger required
- Tag recommended (for traceability)
- Approval recommended (via GitHub environment protection)
- Highest reliability requirements

**Deployment Flow**:

```
Manual Trigger → validate → build → deploy → notify
```

## Error Handling

### Health Check Strategy

**Exponential Backoff**:

- Initial wait: 1 second
- Maximum wait: 60 seconds
- Maximum attempts: 15
- Formula: `wait_time = min(2^(attempt-1), 60)`

**Backoff Sequence**:

```
Attempt 1:  wait 1s
Attempt 2:  wait 2s
Attempt 3:  wait 4s
Attempt 4:  wait 8s
Attempt 5:  wait 16s
Attempt 6:  wait 32s
Attempt 7:  wait 60s
Attempt 8:  wait 60s
...
Attempt 15: wait 60s
```

**Total Maximum Time**: ~15 minutes (worst case)

### Rollback Strategy

**Trigger Conditions**:

- Health check fails after all retries
- Previous version available

**Rollback Process**:

1. **Capture Current State** (before deployment):

   ```bash
   aws lambda get-function --function-name <name>
   # Store: current_image_uri, current_version
   ```

2. **Query Version History** (on failure):

   ```bash
   aws lambda list-versions-by-function --function-name <name>
   # Get: previous version number
   ```

3. **Get Previous Image URI**:

   ```bash
   aws lambda get-function --function-name <name> --qualifier <version>
   # Extract: previous_image_uri
   ```

4. **Rollback Lambda**:

   ```bash
   aws lambda update-function-code \
     --function-name <name> \
     --image-uri <previous_image_uri>
   ```

5. **Verify Rollback**:
   - Health check with exponential backoff (5 attempts)

**Fallback Strategy**:

- Primary: Lambda version history
- Fallback: Captured current image URI

### Failure Notification

**GitHub Issue Creation**:

- Automatic on deployment failure
- Includes: environment, version, commit, workflow link
- Labels: `deployment`, `rollback`, `urgent`, `<environment>`
- Status: Rollback success/failure

## Concurrency Control

### Strategy

**Per-Environment Concurrency**:

```yaml
concurrency:
  group: deploy-${environment}
  cancel-in-progress: false
```

**Behavior**:

- Only one deployment per environment at a time
- Different environments can deploy simultaneously
- Queued deployments wait (don't cancel in-progress)

**Example**:

- Dev deployment running → New dev deployment queued
- Dev deployment running → Staging deployment runs in parallel ✅

## Security Considerations

### Authentication

**AWS**:

- OIDC authentication via GitHub Actions
- Role assumption with session name
- 1-hour session duration

**Docker Registries**:

- GHCR: GitHub token authentication
- ECR: AWS credentials via `docker login`

### Secrets Management

- AWS role ARN: GitHub secrets
- No hardcoded credentials
- Least privilege principle

### Environment Protection

- Staging/Prod: Optional approval gates
- Dev: No approval (auto-deploy)

## Monitoring and Observability

### Deployment Metrics

**Tracked**:

- Deployment success rate
- Deployment duration
- Rollback frequency
- Health check retry count

### Logging

**GitHub Actions**:

- Step-by-step logs
- Error messages
- Timing information

**AWS CloudWatch**:

- Lambda function logs
- API Gateway logs
- Application logs

### Status Checks

**GitHub Status Checks**:

- Deployment status per environment
- Version information
- Rollback status

## Scalability Considerations

### Current Limitations

- Single region deployment (us-east-1)
- Single Lambda function per environment
- No blue/green deployments

### Future Enhancements

1. **Multi-Region**: Deploy to multiple AWS regions
2. **Blue/Green**: Zero-downtime deployments
3. **Canary**: Gradual rollout
4. **Auto-Scaling**: Dynamic resource allocation

## Troubleshooting

### Common Issues

**Health Check Failures**:

- Check application logs in CloudWatch
- Verify API Gateway configuration
- Check Lambda function status

**Rollback Failures**:

- Verify Lambda version history exists
- Check ECR image availability
- Review AWS permissions

**Build Failures**:

- Check Docker build logs
- Verify dependencies
- Check GHCR permissions

### Debug Commands

```bash
# Check Lambda function status
aws lambda get-function --function-name meal-expense-tracker-dev

# List Lambda versions
aws lambda list-versions-by-function --function-name meal-expense-tracker-dev

# Check API Gateway
aws apigatewayv2 get-apis --query "Items[?contains(Name, 'meal-expense-tracker-dev')]"

# Manual health check
curl https://meals.dev.nivecher.com/health
```

## References

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [AWS Lambda Versioning](https://docs.aws.amazon.com/lambda/latest/dg/configuration-versions.html)
- [Terraform Documentation](https://www.terraform.io/docs)
- [Docker Documentation](https://docs.docker.com/)
