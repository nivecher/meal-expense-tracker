# Testing GitHub Actions Workflows Locally with Act

This guide explains how to test GitHub Actions workflows locally using [act](https://github.com/nektos/act).

## Quick Start

### 1. Verify act is installed

```bash
act --version
# Should show: act version 0.2.78 (or similar)
```

### 2. List available workflows and jobs

```bash
# Using Makefile
make act-list

# Or directly with act
act -W .github/workflows/ci.yml --list
```

### 3. Test a simple job (dry run first)

```bash
# Dry run to see what would execute
make act-plan WORKFLOW=ci

# Actually run the lint job
make act-lint

# Or run with custom parameters
make act-run WORKFLOW=ci JOB=lint EVENT=push
```

## Available Commands

### Using Makefile (Recommended)

```bash
# Setup act configuration
make act-setup

# List all workflows/jobs
make act-list

# Run specific jobs
make act-lint          # Run linting job
make act-test          # Run test jobs
make act-security      # Run security scan
make act-terraform     # Run terraform validation

# Run complete workflows
make act-ci            # Run full CI workflow

# Custom runs
make act-run WORKFLOW=ci JOB=lint EVENT=push
make act-pr            # Test pull_request event
make act-dispatch      # Test workflow_dispatch event

# Cleanup
make act-clean         # Clean artifacts and containers
```

### Using Makefile (All Commands)

The Makefile provides comprehensive act support. See all options:

```bash
make act-help  # Show all available commands
```

## What Works Locally

✅ **Can Test:**

- Workflow syntax and structure
- Job dependencies and flow
- Input validation
- Conditional logic
- Basic shell scripts
- Docker Buildx setup (if Docker is available)
- File operations
- Git operations
- Python/Node.js setup
- Most linting and testing steps

❌ **Won't Work Locally:**

- AWS API calls (Lambda, ECR, S3, etc.) - requires real credentials
- GitHub Container Registry authentication - requires GitHub_TOKEN
- Terraform with real AWS backends - requires AWS credentials
- Real secret access - use dummy values in `.secrets`
- GitHub API calls (issues, checks, etc.) - requires GitHub_TOKEN
- Some composite actions may have limitations
- Cache actions may fail without proper inputs

## Configuration Files

### `.actrc` (Act Configuration)

Already configured with:

- Ubuntu runner image
- Artifact server path
- Container options

### `.secrets` (Secrets File)

Create this file with dummy values for local testing:

```bash
# .secrets file
GITHUB_TOKEN=dummy_token_for_local_testing
AWS_ROLE_ARN=arn:aws:iam::123456789012:role/dummy-role
AWS_ACCESS_KEY_ID=dummy_key
AWS_SECRET_ACCESS_KEY=dummy_secret
```

**Note:** These are only for testing workflow structure. Real secrets won't work locally.

### `.env.act` (Environment Variables)

Optional environment variables file:

```bash
PYTHON_VERSION=3.13
NODE_VERSION=22
PYTHONPATH=/github/workspace
FLASK_ENV=test
TESTING=true
```

## Common Issues and Solutions

### Issue: Cache action fails

**Error:** `Input required and not supplied: key`

**Solution:** This is expected in act. Cache actions may fail but workflows can continue. The cache step is optional for local testing.

### Issue: Composite action interpolation errors

**Error:** `Unable to interpolate expression`

**Solution:** Some GitHub Actions expressions don't work perfectly in act. This is a known limitation. The workflow may still run but some steps might fail.

### Issue: Docker-in-Docker not working

**Error:** Docker commands fail inside container

**Solution:** Act runs in Docker, so Docker-in-Docker requires special setup. For local testing, you can:

- Skip Docker build steps
- Use `--dryrun` to see what would execute
- Test Docker builds separately outside act

### Issue: AWS credentials required

**Error:** AWS API calls fail

**Solution:** This is expected. AWS operations require real credentials and won't work locally. Test these workflows in GitHub Actions or use AWS credentials if you have them configured.

## Testing Strategy

### 1. Syntax Validation (No act required)

```bash
# Validate workflow YAML syntax
./scripts/validate-workflow-syntax.sh .github/workflows/ci.yml
```

### 2. Dry Run (See what would execute)

```bash
# See workflow structure without executing
act -W .github/workflows/ci.yml --dryrun
```

### 3. Test Individual Jobs

```bash
# Test linting (most likely to work)
make act-lint

# Test tests (may require setup)
make act-test
```

### 4. Test Complete Workflow

```bash
# Run full CI workflow
make act-ci
```

## Best Practices

1. **Start with dry runs** - See what would execute before running
2. **Test individual jobs first** - Easier to debug than full workflows
3. **Use Makefile commands** - They handle common configurations
4. **Expect some failures** - Not everything works locally
5. **Focus on workflow structure** - Act is best for testing logic, not actual execution
6. **Use real GitHub Actions for final testing** - Some things only work in GitHub

## Troubleshooting

### Act not found

```bash
# Install act
brew install act  # macOS
# Or
curl -s https://raw.githubusercontent.com/nektos/act/master/install.sh | sudo bash  # Linux
```

### Docker not running

```bash
# Start Docker daemon
sudo systemctl start docker  # Linux
# Or start Docker Desktop (macOS/Windows)
```

### Permission errors

```bash
# Add user to docker group (Linux)
sudo usermod -aG docker $USER
# Log out and back in
```

### Artifact server errors

```bash
# Ensure artifact directory exists
mkdir -p /tmp/artifacts
```

## Examples

### Example 1: Test linting job

```bash
# Dry run first
act -W .github/workflows/ci.yml -j lint --dryrun

# Actually run
make act-lint
```

### Example 2: Test with pull request event

```bash
make act-pr
```

### Example 3: Test deploy workflow (will fail on AWS steps)

```bash
# This will fail on AWS steps, but you can see the workflow structure
act -W .github/workflows/deploy.yml workflow_dispatch
```

### Example 4: List all jobs in a workflow

```bash
act -W .github/workflows/ci.yml --list
```

## Additional Resources

- [Act Documentation](https://github.com/nektos/act)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Local Workflows Guide](./LOCAL_WORKFLOWS.md)
- [Workflow Testing Guide](./ACT_TESTING.md)
