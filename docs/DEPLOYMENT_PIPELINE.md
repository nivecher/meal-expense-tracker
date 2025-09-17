# Deployment Pipeline Documentation

## Overview

The Meal Expense Tracker uses a streamlined deployment pipeline that follows the **dev → tag → test → release → staging → prod** flow.

This document describes the new workflow structure and how to use it.

## Workflow Architecture

### 1. CI Workflow (`ci.yml`)

**Purpose**: Continuous Integration - runs on every push and pull request
**Triggers**:

- Push to `main` or `develop` branches
- Pull requests to `main` or `develop` branches

**Jobs**:

- **lint**: Python, JavaScript, CSS, and HTML linting
- **test**: Unit and integration tests with coverage
- **terraform**: Terraform validation and format checking
- **security**: Security scanning with bandit and safety
- **ci-success**: Final status check

### 2. Deploy Workflow (`deploy.yml`)

**Purpose**: Development deployments - runs on main branch pushes
**Triggers**:

- Push to `main` branch
- Manual workflow dispatch

**Jobs**:

- **quality-gate**: Comprehensive testing and linting
- **security-scan**: Enhanced security scanning with CodeQL
- **version-tag**: Automatic version generation and tagging
- **build**: Docker image build and push
- **deploy-dev**: Deploy to development environment
- **deploy-staging**: Deploy to staging environment (manual)
- **deploy-prod**: Deploy to production environment (manual)
- **notify**: Deployment status notifications

### 3. Release Workflow (`release.yml`)

**Purpose**: Production releases - runs on version tags
**Triggers**:

- Push of version tags (e.g., `v1.0.0`)
- Manual workflow dispatch

**Jobs**:

- **quality-gate**: Comprehensive testing and linting
- **security-scan**: Enhanced security scanning with CodeQL
- **build-release**: Docker image build for release
- **deploy-staging**: Deploy to staging environment
- **deploy-prod**: Deploy to production environment (manual)
- **notify**: Release status notifications

## Deployment Flow

### Development Flow

```
1. Developer pushes to main branch
2. CI workflow runs (lint, test, security, terraform)
3. If CI passes, deploy workflow runs
4. Version is automatically generated and tagged
5. Docker image is built and pushed
6. Deploy to dev environment automatically
7. Deploy to staging/prod manually via workflow dispatch
```

### Release Flow

```
1. Developer creates version tag (e.g., v1.0.0)
2. Release workflow runs
3. Quality gate and security scans run
4. Docker image is built for release
5. Deploy to staging automatically
6. Deploy to production manually via workflow dispatch
```

## Local Development Commands

### CI/CD Commands

```bash
# Run local CI workflow
make ci-local

# Run quick CI checks
make ci-quick

# Run local pipeline workflow
make pipeline-local

# Run CI workflow using act
make act-ci

# Run deploy workflow using act
make act-deploy ENV=dev SKIP_TESTS=false

# Run release workflow using act
make act-release ENV=staging TAG=v1.0.0
```

### Deployment Commands

```bash
# Deploy to development
make deploy-dev

# Deploy to staging
make deploy-staging

# Deploy to production
make deploy-prod

# Release to staging (tag-based)
make release-staging TAG=v1.0.0

# Release to production (tag-based)
make release-prod TAG=v1.0.0
```

## Environment Configuration

### Required Secrets

- `GITHUB_TOKEN`: GitHub personal access token
- `AWS_ROLE_ARN`: AWS IAM role for deployment
- `ECR_REGISTRY`: Container registry URL

### Environment Variables

- `ENV`: Target environment (dev, staging, prod)
- `TF_ENV`: Terraform environment
- `AWS_REGION`: AWS region (default: us-east-1)
- `PYTHON_VERSION`: Python version (default: 3.13)
- `NODE_VERSION`: Node.js version (default: 20)

## Workflow Triggers

### Automatic Triggers

- **CI**: Every push to main/develop, every PR
- **Deploy**: Every push to main (dev deployment)
- **Release**: Every version tag push

### Manual Triggers

- **Deploy**: Manual workflow dispatch for staging/prod
- **Release**: Manual workflow dispatch for production

## Quality Gates

### CI Quality Gate

- All linting passes
- All tests pass
- Terraform validation passes
- Security scans pass

### Deploy Quality Gate

- All CI checks pass
- Enhanced security scanning passes
- Docker image builds successfully
- Terraform deployment succeeds

### Release Quality Gate

- All CI checks pass
- Enhanced security scanning passes
- Docker image builds successfully
- Terraform deployment succeeds
- Manual approval for production

## Security Features

### Security Scanning

- **Bandit**: Python security linting
- **Safety**: Python dependency vulnerability scanning
- **CodeQL**: GitHub's semantic code analysis
- **Semgrep**: Static analysis for security issues
- **Grype**: Container vulnerability scanning
- **Detect-secrets**: Secret detection and prevention

### Access Control

- Environment-specific permissions
- Manual approval for production deployments
- Role-based access control (RBAC)
- Audit logging for all deployments

## Monitoring and Notifications

### Deployment Status

- GitHub Actions status checks
- PR comment notifications
- Workflow run notifications
- Deployment verification

### Health Checks

- Load balancer health checks
- Application health endpoints
- Database connectivity checks
- Service availability monitoring

## Troubleshooting

### Common Issues

1. **CI Failures**: Check linting, tests, and security scans
2. **Deployment Failures**: Check AWS credentials and Terraform state
3. **Release Failures**: Verify tag format and environment permissions

### Debug Commands

```bash
# Check environment setup
make validate-env

# Run specific test suites
make test-unit
make test-integration

# Check Terraform configuration
make tf-validate

# View deployment logs
make docker-logs
```

## Best Practices

### Development

1. Always run `make ci-local` before pushing
2. Use feature branches for development
3. Run `make check` before committing
4. Test locally with `make act-ci`

### Deployment

1. Never skip quality gates
2. Always test in dev before staging
3. Use manual approval for production
4. Monitor deployment status

### Release

1. Use semantic versioning (e.g., v1.0.0)
2. Test releases in staging first
3. Get approval before production release
4. Document release notes

## Migration from Old Pipeline

The old `pipeline.yml` has been replaced with the new streamlined workflows:

- **ci.yml**: Handles continuous integration
- **deploy.yml**: Handles development deployments
- **release.yml**: Handles production releases

### Key Changes

1. **Separation of Concerns**: CI, deploy, and release are now separate workflows
2. **Simplified Triggers**: Clearer trigger conditions for each workflow
3. **Better Security**: Enhanced security scanning and access control
4. **Improved Monitoring**: Better status reporting and notifications
5. **Local Testing**: Better support for local workflow testing with act

## Support

For issues or questions about the deployment pipeline:

1. Check the workflow logs in GitHub Actions
2. Review this documentation
3. Test locally with `make act-ci` or `make act-deploy`
4. Contact the development team
