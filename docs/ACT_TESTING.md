# Testing GitHub Actions Workflows Locally with Act

This guide explains how to test GitHub Actions workflows locally using [act](https://github.com/nektos/act).

## Prerequisites

Install `act`:

```bash
# macOS
brew install act

# Linux (using nix)
nix-env -i act

# Or download from: https://github.com/nektos/act/releases
```

## Quick Start

### 0. Validate workflow syntax (no act required)

```bash
# Check workflow YAML syntax and structure
./scripts/validate-workflow-syntax.sh

# Or check a specific workflow
./scripts/validate-workflow-syntax.sh .github/workflows/deploy.yml
```

### 1. List available jobs

```bash
./scripts/test-deploy-workflow.sh dev --list
```

### 2. Dry run (see what would execute)

```bash
./scripts/test-deploy-workflow.sh dev --dry-run
```

### 3. Run the workflow (with limitations)

```bash
# Test with default environment (dev)
./scripts/test-deploy-workflow.sh

# Test with specific environment
./scripts/test-deploy-workflow.sh staging

# Test with environment and image tag
./scripts/test-deploy-workflow.sh dev v1.0.0
```

## Configuration

### Secrets File

Create a `.secrets` file (or copy from `.secrets.example`):

```bash
cp .secrets.example .secrets
# Edit .secrets with your test values (or leave empty for local testing)
```

**Note**: Most secrets won't work locally (AWS_ROLE_ARN, GitHub_TOKEN, etc.), but you can use dummy values to test the workflow structure.

### Act Configuration

The `.actrc` file contains act configuration:

- Uses `catthehacker/ubuntu:act-latest` runner image
- Enables artifact server
- Sets up container options

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

❌ **Won't Work Locally:**

- AWS API calls (Lambda, ECR, S3, etc.)
- GitHub Container Registry authentication
- Terraform with real AWS backends
- Real secret access
- GitHub API calls (issues, checks, etc.)

## Testing Specific Jobs

You can test individual jobs:

```bash
# Test only the validate job
act workflow_dispatch -W .github/workflows/deploy.yml \
  --input environment=dev \
  --job validate

# Test only the build job (will fail on AWS steps)
act workflow_dispatch -W .github/workflows/deploy.yml \
  --input environment=dev \
  --job build
```

## Mocking AWS Services

For more realistic testing, you can use local AWS mocks:

```bash
# Install LocalStack (Docker required)
docker run -d -p 4566:4566 localstack/localstack

# Set AWS endpoint to LocalStack
export AWS_ENDPOINT_URL=http://localhost:4566
export AWS_ACCESS_KEY_ID=test
export AWS_SECRET_ACCESS_KEY=test
export AWS_DEFAULT_REGION=us-east-1
```

Then run act with these environment variables.

## Troubleshooting

### Docker Issues

If Docker commands fail in act:

- Ensure Docker is running: `docker ps`
- Act needs Docker to run workflows
- Some Docker actions may not work perfectly locally

### Permission Issues

If you get permission errors:

- Act runs in containers, so file permissions may differ
- Use `--bind` flag (already in `.actrc`) for better file access

### Missing Actions

Some GitHub Actions may not work locally:

- Custom actions may need to be mocked
- Some actions require GitHub API access
- Check act's compatibility: https://github.com/nektos/act#known-limitations

### Large Workflows

For complex workflows:

- Test individual jobs first
- Use `--dry-run` to see what would execute
- Skip problematic steps with `--skip-job`

## Example: Testing the Validate Job

The validate job is a good candidate for local testing since it doesn't require AWS:

```bash
act workflow_dispatch \
  -W .github/workflows/deploy.yml \
  --input environment=dev \
  --input image_tag=test-v1.0.0 \
  --job validate \
  --secret-file .secrets
```

## CI/CD Integration

While act is great for local testing, remember:

- Always test in GitHub Actions for final validation
- Some differences exist between act and real GitHub Actions
- Use act for rapid iteration, GitHub Actions for final verification

## Resources

- [Act Documentation](https://github.com/nektos/act)
- [Act Examples](https://github.com/nektos/act-examples)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
