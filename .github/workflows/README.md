# GitHub Actions Workflows

This directory contains the CI/CD workflows for the Meal Expense Tracker application.

## Philosophy: Simplicity Over Complexity

This project follows a **minimalist approach** to GitHub Actions:

- **Prefer Native Actions**: Use official GitHub actions over custom wrappers
- **Inline Over Abstraction**: Keep logic visible and maintainable
- **Composite Actions**: `setup-python-env`, `generate-version`, `generate-backend-hcl` for shared logic
- **Build Once, Deploy Many**: A single build (per commit on `main`) produces the GHCR image; deploy reuses it via `image_tag` without rebuilding
- **No Reusable Workflows**: Use `workflow_run` and `workflow_dispatch` for sequencing; no `workflow_call`

### Why This Approach?

**Before** (Over-engineered):
- 4 composite actions (535 lines of custom code)
- 4 reusable workflows (cluttering Actions tab)
- Multiple layers of indirection
- Harder to debug and maintain

**After** (Simplified):
- 1 composite action (110 lines)
- Native GitHub actions for everything else
- Clear, inline logic
- Easy to understand and modify

## Workflows

### 1. CI (`ci.yml`)

**Trigger**: Push/PR to `main` or `develop` branches

**Jobs**:
- **lint**: Python/JavaScript/YAML/JSON/TOML linting
- **test**: Unit and integration tests with coverage
- **terraform**: Terraform validation and planning
- **security**: Bandit and Safety security scans
- **ci-success**: Aggregates all job statuses

**Key Features**:
- Matrix strategy for parallel test execution (unit + integration)
- Coverage reporting to Codecov
- Test result publishing with EnricoMi/publish-unit-test-result-action
- Job-level permissions (least privilege)
- Rich job summaries

**Usage**:
```bash
# Automatically runs on push/PR
# To run manually:
gh workflow run ci.yml
```

---

### 2. Tag (`tag.yml`)

**Trigger**:
- `workflow_run` after successful **CI** on `main` (main-only)
- Manual via `workflow_dispatch` (main branch only)

**Jobs**:
- **check-ci-and-branch**: Ensure CI succeeded and branch is `main`
- **create-tag**: Run `determine_version`, create and push git tag when bump needed

**Key Features**:
- **Tag-then-build** (recommended): Tag runs after CI; Build runs after Tag. Git tag exists before image.
- Tags only on `main`; creates tag only when `BUMP_NEEDED` (conventional commits). Use `force: true` to tag anyway.
- Semantic version generation; duplicate tag protection; changelog preview in summary

**Usage**:
```bash
# Automatically runs after CI on main
# Manual (from main only):
gh workflow run tag.yml
# Force tag even if no bump:
gh workflow run tag.yml -f force=true
```

---

### 3. Build (`build.yml`)

**Trigger**: `workflow_run` after **Tag** completes (success or no-op)

**Jobs**:
- **build**: Determine version, build and push Docker image (lambda, linux/amd64) to GHCR, upload SBOM

**Key Features**:
- Runs after every Tag run (tag created or not). Image tagged with version and short SHA.
- Uses `determine_version` (same logic as Tag); SBOM and provenance attestations

---

### 4. Deploy (`deploy.yml`)

**Trigger**:
- `workflow_run` after successful **Build** on `main` (deploys to **dev**, reuses built image)
- Manual via `workflow_dispatch`

**Jobs**:
- **validate**: Resolve environment and `image_tag`; set `skip_build` when image already exists
- **build**: Build and push Docker image (only when `skip_build` is false, e.g. manual deploy without `image_tag`)
- **deploy**: Deploy infrastructure and Lambda; pull image from GHCR by `image_tag`
- **notify**: Deployment status

**Key Features**:
- Deploy-only when triggered by Build or when `image_tag` is provided (build-once, deploy-many)
- Multi-environment support (dev, staging, prod)
- AWS OIDC authentication (no long-lived credentials)
- Terraform infrastructure management
- Automatic rollback on failure
- Health check validation

**Usage**:
```bash
# Deploy to dev (runs automatically after Build on main)
# Deploy to staging with a specific version
gh workflow run deploy.yml -f environment=staging -f image_tag=1.2.3

# Deploy to prod
gh workflow run deploy.yml -f environment=prod -f image_tag=1.2.3
```

---

### 5. Test (`test.yml`)

**Trigger**: 
- `workflow_run` after successful deployment
- Manual via `workflow_dispatch`

**Jobs**:
- **check-deploy**: Validate deployment succeeded
- **health-checks**: Endpoint health validation
- **API-tests**: API integration tests
- **e2e-tests**: Playwright end-to-end tests
- **test-summary**: Aggregate test results

**Key Features**:
- Configurable test suite selection (all, health, API, e2e)
- Custom deployment URL support
- Retry logic for health checks
- Playwright HTML reports
- Conditional test execution based on input

**Usage**:
```bash
# Run all tests against production
gh workflow run test.yml -f deployment_url=https://meals.nivecher.com

# Run only E2E tests
gh workflow run test.yml -f test_suite=e2e
```

---

### 6. Release (`release.yml`)

**Trigger**:
- Push of version tags (`v*`)
- Manual via `workflow_dispatch`

**Jobs**:
- **validate-tag**: Resolve tag (from push, input, or latest `vX.Y.Z` on main by semver)
- **verify-image**: Ensure GHCR image exists for that version (no rebuild)
- **create-release**: Create GitHub release and changelog
- **trigger-staging-deploy**: Dispatch `deploy.yml` with `environment=staging` and `image_tag` (manual-only staging deploy)
- **notify**: Release status

**Key Features**:
- No reusable workflows; no duplicate build (uses existing image)
- Optional tag input; defaults to latest semver tag on main when omitted
- Release creates the GitHub release; then triggers staging deploy via API

**Usage**:
```bash
# Use latest vX.Y.Z on main
gh workflow run release.yml

# Create release from specific tag
gh workflow run release.yml -f tag=v1.2.3
```

---

---

## Composite Actions

### `setup-python-env`

**Location**: `.github/actions/setup-python-env/`

**Purpose**: Centralize Python environment setup with project-specific logic

**Inputs**:
- `python-version`: Python version to use (required)
- `requirements-file`: Requirements file to install (default: `requirements-dev.txt`)
- `cache-key-suffix`: Additional cache key suffix (optional)
- `skip-venv`: Skip virtual environment creation (default: `false`)

**Outputs**:
- `cache-hit`: Whether the cache was hit
- `python-path`: Path to Python executable

**Why Keep This?**:
- ✅ Used in 3+ workflows (high reuse)
- ✅ Handles project-specific SQLAlchemy stubs cleanup
- ✅ Complex venv + caching logic (90+ lines saved per usage)
- ✅ Proper activation that's tricky to get right

**Usage**:
```yaml
- name: Setup Python Environment
  uses: ./.github/actions/setup-python-env
  with:
    python-version: 3.13
    requirements-file: requirements-dev.txt
```

---

## Native Actions Used

### Core GitHub Actions
- `actions/checkout@v4.2.2` - Repository checkout
- `actions/setup-python@v5.3.0` - Python installation
- `actions/setup-node@v4.1.0` - Node.js installation
- `actions/cache@v4.2.0` - Dependency caching
- `actions/upload-artifact@v4.6.0` - Artifact uploads

### AWS & Infrastructure
- `aws-actions/configure-aws-credentials@v4` - AWS OIDC authentication
- `hashicorp/setup-terraform@v3.1.2` - Terraform setup

### Docker
- `docker/setup-buildx-action@v3.8.0` - Docker Buildx setup
- `docker/login-action@v3.3.0` - Container registry login
- `docker/build-push-action@v6.10.0` - Multi-platform builds
- `docker/metadata-action@v5.6.1` - Image metadata generation

### Security & Quality
- `github/codeql-action/*` - CodeQL security analysis (use GitHub's built-in CodeQL setup)
- `codecov/codecov-action@v4` - Code coverage reporting
- `EnricoMi/publish-unit-test-result-action@v2` - Test result publishing

---

## Secrets Required

| Secret             | Description                     | Usage                 |
| ------------------ | ------------------------------- | --------------------- |
| `AWS_ROLE_ARN`     | AWS IAM role ARN for OIDC       | Deploy, CI (Terraform)|
| `GITHUB_TOKEN`     | Auto-provided by GitHub         | All workflows         |

---

## Environment Variables

### Common Variables
```yaml
PYTHON_VERSION: 3.13
NODE_VERSION: 22
FLASK_ENV: test
TESTING: true
```

### Deployment Variables
```yaml
AWS_REGION: us-east-1
TF_PARALLELISM: 30
TF_IN_AUTOMATION: 1
```

---

## Local Testing with Act

Test workflows locally using [act](https://github.com/nektos/act):

```bash
# List all workflows and jobs
act --list

# Test CI lint job
act -j lint

# Test with specific event
act push

# Dry run to see what would execute
act --dryrun
```

**Note**: Some jobs (AWS authentication, Terraform) cannot run locally without proper credentials.

---

## Workflow Diagram

```
┌─────────────┐
│   Push/PR   │
└─────┬───────┘
      │
      ▼
┌─────────────┐
│   CI.yml    │  Lint, Test, Security, Terraform
└─────┬───────┘
      │ (on main)
      ▼
┌─────────────┐
│  Tag.yml    │  Create version tag (main only; bump when conventional commits)
└─────┬───────┘
      │
      ▼
┌─────────────┐
│ Build.yml   │  Build image → push GHCR
└─────┬───────┘
      │
      ▼
┌──────────────┐
│ Deploy.yml   │  Dev deploy (reuses image)
└─────┬────────┘
      │
      │  Manual: Release.yml → create release → trigger deploy (staging)
      │          deploy.yml dispatch (staging/prod + image_tag)
      ▼
┌──────────────┐
│   Test.yml   │  Smoke/E2E
└──────────────┘
```

---

## Troubleshooting

### Common Issues

**1. Workflow not triggering**
- Check branch filters in `on:` section
- Verify file paths in `paths-ignore:`
- Check if workflow is enabled in Settings > Actions

**2. Tests failing**
- Review test artifacts in workflow run
- Check test summaries in job output
- Run tests locally: `pytest tests/`

**3. Deployment failing**
- Verify AWS credentials are valid
- Check Terraform state is not locked
- Review deployment logs and rollback if needed

**4. Cache not hitting**
- Cache keys include file hashes
- Check if dependencies changed
- Manual cache clear: Settings > Actions > Caches

### Getting Help

- View workflow runs: Actions tab on GitHub
- Download artifacts for detailed logs
- Check job summaries for quick diagnostics
- Review [GitHub Actions documentation](https://docs.github.com/en/actions)

---

## Best Practices

### ✅ DO
- Use native GitHub actions when possible
- Keep inline logic simple and readable
- Add job summaries for observability
- Use matrix strategies for parallel execution
- Set job-level permissions (least privilege)
- Cache dependencies appropriately
- Include health checks after deployments

### ❌ DON'T
- Create composite actions for single-use logic
- Create reusable workflows that clutter Actions tab
- Use long-lived AWS credentials
- Skip security scanning
- Ignore failed tests in CI
- Deploy without validation

---

## Contributing

When modifying workflows:

1. **Test locally** with `act` when possible
2. **Validate YAML** syntax before committing
3. **Update this README** with any changes
4. **Keep it simple** - prefer inline over abstraction
5. **Add summaries** to new jobs for observability

---

**Last Updated**: January 2026  
**Flow**: CI → Tag (main only) → Build → Deploy (dev). Tag-then-build; tag created only when bump needed (conventional commits). Release (manual) creates release and triggers staging deploy. Build-once, deploy-many; no reusable workflows.

**Standards**: Commit messages enforced via [commitlint](https://commitlint.js.org/) (pre-commit `commit-msg` hook + CI). Versioning via [Python-semantic-release](https://python-semantic-release.readthedocs.io/); `scripts/determine_version.py` is a thin wrapper that outputs `NEXT_VERSION` / `NEW_TAG` / `BUMP_NEEDED` for workflows.
