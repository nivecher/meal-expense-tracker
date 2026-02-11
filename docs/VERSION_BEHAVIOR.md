# Version Behavior Documentation

This document describes how version is determined across different contexts to ensure consistency.

## Version Determination Rules

### On Main Branch

**Rule**: When on the `main` branch, use the **latest git tag version** directly (no post-release versions).

This ensures:

- `make version` shows the tag version
- CI/deploy workflows use the tag version
- Deployments from main use the tag version (not post versions)

### On Other Branches

**Rule**: Use `setuptools-scm` with `no-guess-dev` scheme (may show post-release versions).

This allows:

- Development branches to show they're ahead of the tag
- Post-release versions like `0.6.1.post1.dev3+gabc123.d20251207`

## Version Sources

### 1. `make version` Command

**Location**: `Makefile` → calls `scripts/get_version.py`

**Behavior**:

- On `main`: Returns latest tag version (e.g., `0.6.1`)
- On other branches: Uses setuptools-scm (may show post versions)

**Example**:

```bash
# On main branch with tag v0.6.1
$ make version
0.6.1

# On feature branch with commits after tag
$ make version
0.6.1.post1.dev3+gabc123.d20251207
```

### 2. CI/Deploy Workflows

**Location**: `.github/workflows/deploy.yml` → `Determine image tag and version` step

**Behavior**:

- Fetches latest tag
- Extracts version (removes 'v' prefix)
- Passes as `explicit_version` to `generate-version` action
- Result: Tag version is used (e.g., `0.6.1`)

**Code**:

```yaml
git fetch --tags --force || true
LATEST_TAG=$(git describe --tags --abbrev=0 2>/dev/null || echo "")
if [ -n "${LATEST_TAG}" ]; then
VERSION=$(echo "${LATEST_TAG}" | sed 's/^v//')
fi
```

### 3. Version File Generation

**Location**: `.github/actions/generate-version` → calls `scripts/generate_version_file.py`

**Behavior**:

- If `explicit_version` provided: Write it directly
- Otherwise: Use setuptools-scm (reads from `pyproject.toml`)

**Usage in Deploy**:

```yaml
- uses: ./.github/actions/generate-version
  with:
    explicit_version: ${{ needs.validate.outputs.version }} # Tag version from deploy workflow
```

### 4. Docker Build

**Location**: `.github/workflows/reusable/docker-build.yml`

**Behavior**:

- Receives `version` input from calling workflow
- Passes to `generate-version` action as `explicit_version`
- Result: Tag version is written to `app/_version.py`

## Consistency Check

### ✅ Aligned Behaviors

1. **Main Branch**:
   - `make version` → Tag version
   - Deploy workflow → Tag version
   - Docker build → Tag version
   - Version file → Tag version

2. **Other Branches**:
   - `make version` → setuptools-scm (may show post versions)
   - Development builds → setuptools-scm (may show post versions)

### Verification

To verify version behavior:

```bash
# Check current version (should match tag on main)
make version

# Check what deploy workflow would use
git fetch --tags --force
git describe --tags --abbrev=0 | sed 's/^v//'

# Check version file
cat app/_version.py | grep __version__
```

## Implementation Details

### Scripts

- **`scripts/get_version.py`**:
  - Checks if on `main` branch
  - If yes: Uses latest tag version
  - If no: Uses setuptools-scm

- **`scripts/generate_version_file.py`**:
  - If version argument provided: Writes it directly
  - Otherwise: Uses setuptools-scm

### Configuration

- **`pyproject.toml`**: Configures setuptools-scm with `no-guess-dev` scheme
- **Deploy workflow**: Determines tag version and passes explicitly
- **Docker build**: Receives version and passes to generate-version action

## Summary

**On main branch**: All version sources use the **tag version** directly (no post-release versions).

**On other branches**: Version sources use **setuptools-scm** (may show post-release versions for development).

This ensures:

- ✅ Deployments from main show clean tag versions
- ✅ Development branches show they're ahead of tag
- ✅ Consistency between `make version` and CI/deploy workflows
