# Local GitHub Actions Workflow Execution

This document explains how to run GitHub Actions workflows locally before committing changes.

## Overview

There are two main approaches to run GitHub Actions workflows locally:

1. **Shell Script Equivalents** (Recommended) - Direct execution of workflow steps
2. **act Tool** - Uses Docker to run actual GitHub Actions workflows

## Quick Start

### Option 1: Shell Script Equivalents (Fastest)

```bash
# Run local CI workflow (equivalent to ci.yml)
make ci-local

# Run quick CI checks (lint + unit tests only)
make ci-quick

# Run local pipeline workflow (equivalent to pipeline.yml)
make pipeline-local

# Run pipeline with specific environment
make pipeline-local ENV=staging TF_APPLY=true
```

### Option 2: Using act (Most Accurate)

```bash
# Setup act first
./scripts/setup-act.sh

# Run CI workflow using act
make act-ci

# Run pipeline workflow using act
make act-pipeline ENV=dev TF_APPLY=false
```

## Detailed Setup

### Shell Script Approach

The shell scripts mirror your GitHub Actions workflows exactly:

- `scripts/local-ci.sh` - Mirrors `.github/workflows/ci.yml`
- `scripts/local-pipeline.sh` - Mirrors `.github/workflows/pipeline.yml`

**Advantages:**

- Fast execution (no Docker overhead)
- Easy to debug and modify
- Works with your existing development environment
- No additional tools required

**Usage:**

```bash
# Run full CI locally
./scripts/local-ci.sh

# Run pipeline locally
./scripts/local-pipeline.sh dev false
```

### act Tool Approach

`act` runs GitHub Actions workflows locally using Docker containers.

**Setup:**

```bash
# Install act
curl https://raw.githubusercontent.com/nektos/act/master/install.sh | sudo bash

# Setup configuration
./scripts/setup-act.sh

# Create .env.local with your secrets
cp scripts/act-config.env .env.local
# Edit .env.local with your actual values
```

**Configuration Files:**

- `.actrc` - act configuration
- `.env.local` - Environment variables and secrets
- `scripts/act-config.env` - Template for environment variables

**Usage:**

```bash
# List available workflows
act -l

# Run CI workflow
act -W .github/workflows/ci.yml

# Run pipeline workflow
act -W .github/workflows/pipeline.yml --input environment=dev --input terraform_apply=false

# Run with specific event
act push -W .github/workflows/ci.yml
```

## Makefile Commands

### Local CI/CD Commands

| Command               | Description                                              |
| --------------------- | -------------------------------------------------------- |
| `make ci-local`       | Run local CI workflow (equivalent to ci.yml)             |
| `make ci-quick`       | Run quick CI checks (lint + unit tests)                  |
| `make pipeline-local` | Run local pipeline workflow (equivalent to pipeline.yml) |
| `make act-ci`         | Run CI workflow using act                                |
| `make act-pipeline`   | Run pipeline workflow using act                          |

### Environment Variables

| Variable   | Default | Description                        |
| ---------- | ------- | ---------------------------------- |
| `ENV`      | `dev`   | Target environment for pipeline    |
| `TF_APPLY` | `false` | Whether to apply Terraform changes |
| `TF_ENV`   | `dev`   | Terraform environment              |

**Examples:**

```bash
# Run pipeline for staging environment
make pipeline-local ENV=staging TF_APPLY=true

# Run act pipeline for production
make act-pipeline ENV=prod TF_APPLY=false
```

## Workflow Comparison

### CI Workflow (ci.yml equivalent)

**Local Execution:** `make ci-local` or `./scripts/local-ci.sh`

**Steps:**

1. ✅ Setup Python 3.13
2. ✅ Setup Node.js 22
3. ✅ Install dependencies
4. ✅ Run linting (Python, JS, CSS, HTML)
5. ✅ Run tests (unit, integration)
6. ✅ Terraform validation
7. ✅ Security scanning (bandit, safety)

### Pipeline Workflow (pipeline.yml equivalent)

**Local Execution:** `make pipeline-local` or `./scripts/local-pipeline.sh`

**Steps:**

1. ✅ Quality Gate (tests, lint, security)
2. ✅ Enhanced Security Scan
3. ✅ Version Tagging
4. ✅ Build Docker image
5. ✅ Terraform (init, plan, optionally apply)
6. ✅ Deploy simulation

## Troubleshooting

### Common Issues

**1. Permission Denied**

```bash
# Make scripts executable
chmod +x scripts/*.sh
```

**2. Missing Dependencies**

```bash
# Install development dependencies
make setup
```

**3. act Docker Issues**

```bash
# Check Docker is running
docker --version

# Pull act images
act -P ubuntu-latest=catthehacker/ubuntu:act-latest --dryrun
```

**4. Environment Variables**

```bash
# Check .env.local exists and has correct values
cat .env.local

# Verify environment setup
make validate-env
```

### Debugging

**Shell Script Debugging:**

```bash
# Run with debug output
bash -x scripts/local-ci.sh

# Run individual steps
make lint-python
make test-unit
make tf-validate
```

**act Debugging:**

```bash
# Verbose output
act -W .github/workflows/ci.yml --verbose

# Dry run to see what would be executed
act -W .github/workflows/ci.yml --dryrun

# List all jobs
act -W .github/workflows/ci.yml --list
```

## Integration with Development Workflow

### Pre-commit Integration

Add to `.pre-commit-config.yaml`:

```yaml
- repo: local
  hooks:
    - id: ci-quick
      name: Quick CI checks
      entry: make ci-quick
      language: system
      pass_filenames: false
```

### IDE Integration

**VS Code Tasks:**

```json
{
  "version": "2.0.0",
  "tasks": [
    {
      "label": "Run Local CI",
      "type": "shell",
      "command": "make ci-local",
      "group": "test"
    },
    {
      "label": "Run Local Pipeline",
      "type": "shell",
      "command": "make pipeline-local",
      "group": "test"
    }
  ]
}
```

## Best Practices

1. **Run Local CI Before Committing**

   ```bash
   make ci-quick  # Fast checks
   # or
   make ci-local  # Full CI
   ```

2. **Test Pipeline Before Tagging**

   ```bash
   make pipeline-local ENV=dev TF_APPLY=false
   ```

3. **Use act for Final Validation**

   ```bash
   make act-ci  # Most accurate to GitHub Actions
   ```

4. **Keep .env.local Secure**
   - Never commit `.env.local`
   - Use `.env.local.template` for sharing
   - Rotate secrets regularly

## Performance Tips

- **Shell Scripts**: Fastest, use for development
- **act**: Most accurate, use for final validation
- **ci-quick**: Use for frequent checks during development
- **ci-local**: Use before committing
- **pipeline-local**: Use before creating releases

## Security Considerations

- Store secrets in `.env.local` (not committed)
- Use least-privilege AWS credentials
- Rotate GitHub tokens regularly
- Don't run Terraform apply locally unless necessary
