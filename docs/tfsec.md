# TFSec Integration

This project uses [TFSec](https://aquasecurity.github.io/tfsec/) for static analysis of Terraform configurations to detect potential security issues.

## Installation

### macOS
```bash
brew install tfsec
```

### Linux
```bash
curl -s https://raw.githubusercontent.com/aquasecurity/tfsec/master/scripts/install_linux.sh | bash
```

### Windows (using Chocolatey)
```bash
choco install tfsec
```

## Usage

### Run TFSec Manually
To scan your Terraform code:
```bash
tfsec .
```

### Run with Specific Output Format
```bash
tfsec -f json .          # JSON output
tfsec -f junit .        # JUnit XML output
tfsec -f csv .          # CSV output
```

### Exclude Specific Checks
To exclude specific checks:
```bash
tfsec --exclude AWS048 .  # Exclude a specific check
```

## Pre-commit Hook

TFSec is integrated into the project's pre-commit hooks. It will automatically run on every commit that includes `.tf` files.

### Skip TFSec in Pre-commit
To skip TFSec checks for a single commit:
```bash
git commit -m "Your message" --no-verify
```

## Configuration

TFSec configuration can be customized by creating a `.tfsec.yml` file in the root of your project. For example:

```yaml
exclude:
  - AWS048  # Disable specific checks
  - GEN001  # Disable generic checks

severity: WARNING  # Only show warnings and above
```

## Ignoring Issues

To ignore specific issues, add a comment in your Terraform code:

```hcl
# tfsec:ignore:AWS017
resource "aws_s3_bucket" "example" {
  # This will be ignored by tfsec
  bucket = "example"
}
```

## CI/CD Integration

### GitHub Actions
Add this to your workflow file:

```yaml
- name: Run TFSec
  uses: aquasecurity/tfsec-action@v1.0.0
  with:
    soft_fail: true  # Set to false to fail the build on issues
```

## Learning Resources

- [TFSec Documentation](https://aquasecurity.github.io/tfsec/)
- [Available Checks](https://aquasecurity.github.io/tfsec/latest/checks/)
- [GitHub Repository](https://github.com/aquasecurity/tfsec)
