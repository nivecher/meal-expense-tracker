# Trivy Integration

This project uses [Trivy](https://aquasecurity.github.io/trivy/) for comprehensive security scanning of Terraform configurations and other artifacts to detect potential security issues.

## Installation

### macOS

```bash
brew install aquasecurity/trivy/trivy
```

### Linux

Using Homebrew:
```bash
brew install aquasecurity/trivy/trivy
```

Or using the official installation script:
```bash
curl -sfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh | sh -s -- -b /usr/local/bin
```

### Windows (with Chocolatey)

```bash
choco install trivy
```

## Usage

### Run Trivy Manually

```bash
# From the project root
cd terraform
trivy config .
```

### Output Formats

Trivy supports multiple output formats:

```bash
trivy config -f json .          # JSON output
trivy config -f template --template "{{ range .Results }}{{ .Target }}:{{ range .Vulnerabilities }} [{{ .VulnerabilityID }}]{{ end }}{{ "\n" }}{{ end }}" .  # Custom template
```

### Ignoring Issues

You can ignore specific checks by creating a `.trivyignore` file in your project root:

```
# Acceptable Risk: This is a false positive
CVE-2023-1234

# This is a test environment
AVD-AWS-0123
```

Or inline in your Terraform files:

```hcl
#trivy:ignore:AVD-AWS-0123
resource "aws_s3_bucket" "example" {
  # ...
}
```

## Integration

### Pre-commit Hooks

Trivy is integrated into the project's pre-commit hooks. It will automatically run on every commit that includes `.tf` files.

### Skip Trivy in Pre-commit

To skip Trivy checks for a single commit:

```bash
git commit -m "Your commit message" --no-verify
```

## GitHub Actions

Example GitHub Actions workflow for Trivy:

```yaml
name: Security Scan

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  security-scan:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3

    - name: Run Trivy vulnerability scanner
      uses: aquasecurity/trivy-action@master
      with:
        scan-type: 'config'
        format: 'sarif'
        output: 'trivy-results.sarif'

    - name: Upload Trivy scan results to GitHub Security tab
      uses: github/codeql-action/upload-sarif@v2
      with:
        sarif_file: 'trivy-results.sarif'
```

## Resources

- [Trivy Documentation](https://aquasecurity.github.io/trivy/latest/)
- [Terraform Scanning](https://aquasecurity.github.io/trivy/latest/docs/scanner/terraform/)
- [GitHub Repository](https://github.com/aquasecurity/trivy)
- [GitHub Action](https://github.com/aquasecurity/trivy-action)
