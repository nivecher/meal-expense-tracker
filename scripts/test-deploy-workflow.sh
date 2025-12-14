#!/bin/bash
# Test the deploy workflow locally using act
# Usage: ./scripts/test-deploy-workflow.sh [environment] [image_tag] [--list|--dry-run|--job JOB_NAME|--include-notify]
#
# Examples:
#   ./scripts/test-deploy-workflow.sh dev                    # Test full workflow (skips notify job)
#   ./scripts/test-deploy-workflow.sh dev v1.0.0            # Test with image tag
#   ./scripts/test-deploy-workflow.sh dev "" --list          # List jobs
#   ./scripts/test-deploy-workflow.sh dev "" --job validate  # Test only validate job
#   ./scripts/test-deploy-workflow.sh dev "" --include-notify # Include notify job (will fail without GitHub App)

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if act is installed
if ! command -v act &> /dev/null; then
    echo -e "${RED}❌ act is not installed${NC}"
    echo "Install it with:"
    echo "  brew install act  # macOS"
    echo "  or visit: https://github.com/nektos/act#installation"
    exit 1
fi

# Get environment from argument or default to dev
ENVIRONMENT=${1:-dev}
IMAGE_TAG=${2:-}

echo -e "${GREEN}🧪 Testing deploy workflow locally with act${NC}"
echo "Environment: ${ENVIRONMENT}"
if [ -n "${IMAGE_TAG}" ]; then
    echo "Image Tag: ${IMAGE_TAG}"
fi
echo ""

# Check if .secrets file exists
if [ ! -f .secrets ]; then
    echo -e "${YELLOW}⚠️  .secrets file not found${NC}"
    echo "Creating .secrets from .secrets.example..."
    if [ -f .secrets.example ]; then
        cp .secrets.example .secrets
        echo -e "${YELLOW}⚠️  Please edit .secrets with your test values${NC}"
    else
        touch .secrets
        echo "# Secrets file for act testing" > .secrets
        echo "# Add GITHUB_TOKEN=your_token_here to avoid git auth errors" >> .secrets
    fi
fi

# Check if GITHUB_TOKEN is in secrets (helps with checkout action)
if [ -f .secrets ] && grep -q "GITHUB_TOKEN" .secrets 2>/dev/null; then
    if ! grep -q "GITHUB_TOKEN=.*[^=]$" .secrets 2>/dev/null || grep -q "GITHUB_TOKEN=$" .secrets 2>/dev/null; then
        echo -e "${YELLOW}💡 Tip: Add GITHUB_TOKEN to .secrets to help with checkout authentication${NC}"
        echo "   Create a token at: https://github.com/settings/tokens"
        echo "   (Use a classic token with 'repo' scope for private repos)"
    fi
fi

# Configure git to avoid authentication issues with act
# This sets up git to use local filesystem only (no remote operations)
if git rev-parse --git-dir > /dev/null 2>&1; then
    # Check if we have a remote configured
    if git remote get-url origin > /dev/null 2>&1; then
        REMOTE_URL=$(git remote get-url origin)
        # If remote uses HTTPS and might require auth, we'll handle it in the container
        echo -e "${GREEN}✓ Git repository detected${NC}"
        echo "  Remote: ${REMOTE_URL}"
    fi
fi

# Get GitHub repository info
GITHUB_REPO=$(git config --get remote.origin.url 2>/dev/null | sed 's/.*github.com[:/]\(.*\)\.git/\1/' || echo 'test/repo')
GITHUB_SHA=$(git rev-parse HEAD 2>/dev/null || echo 'test-sha')

# Build act command as array for proper argument handling
ACT_ARGS=(
    "workflow_dispatch"
    "-W" ".github/workflows/deploy.yml"
    "--input" "environment=${ENVIRONMENT}"
    "--bind"  # Use local filesystem (important for local actions)
    "--use-gitignore"  # Respect .gitignore when copying files
)

# Add image tag input if provided
if [ -n "${IMAGE_TAG}" ]; then
    ACT_ARGS+=("--input" "image_tag=${IMAGE_TAG}")
fi

# Skip notify job by default (requires GitHub App auth for check runs)
# User can explicitly include it with --include-notify
SKIP_NOTIFY=true
for arg in "$@"; do
    if [ "$arg" = "--include-notify" ]; then
        SKIP_NOTIFY=false
        break
    fi
done

if [ "$SKIP_NOTIFY" = "true" ]; then
    ACT_ARGS+=("--input" "skip_notify=true")
    echo -e "${YELLOW}💡 'notify' job will be skipped (requires GitHub App auth for check runs)${NC}"
    echo -e "${YELLOW}   Use --include-notify to test it (will fail without GitHub App)${NC}"
fi

# Add secrets file if it exists
if [ -f .secrets ]; then
    ACT_ARGS+=("--secret-file" ".secrets")
fi

# Add environment variables using --env flag (more reliable than -e)
ACT_ARGS+=(
    "--env" "GITHUB_ACTOR=test-user"
    "--env" "GITHUB_REPOSITORY=${GITHUB_REPO}"
    "--env" "GITHUB_SHA=${GITHUB_SHA}"
    "--env" "GITHUB_REF=refs/heads/main"
    "--env" "ACT_BIND=true"  # Tell act to use bind mounts
    "--env" "GIT_TERMINAL_PROMPT=0"  # Prevent git from prompting for credentials
    "--env" "GIT_ASKPASS="  # Disable git credential helper
    "--env" "GIT_CONFIG_NOSYSTEM=1"  # Don't use system git config
    "--env" "GIT_CONFIG_GLOBAL=/dev/null"  # Don't use global git config
)

# Check if we're in a git repository and configure accordingly
if git rev-parse --git-dir > /dev/null 2>&1; then
    # Get the current branch
    CURRENT_BRANCH=$(git branch --show-current 2>/dev/null || echo "main")
    ACT_ARGS+=("--env" "GITHUB_REF=refs/heads/${CURRENT_BRANCH}")
    echo -e "${GREEN}✓ Detected git repository on branch: ${CURRENT_BRANCH}${NC}"
else
    echo -e "${YELLOW}⚠️  Not in a git repository, using defaults${NC}"
fi

# Add list flag to show what would run
if [ "${3}" = "--list" ]; then
    echo -e "${GREEN}📋 Listing jobs that would run:${NC}"
    act "${ACT_ARGS[@]}" --list
    exit 0
fi

# Add dry-run flag
if [ "${3}" = "--dry-run" ]; then
    echo -e "${GREEN}🔍 Dry run mode (will show what would execute):${NC}"
    ACT_ARGS+=("--dryrun")
fi

# Check if user wants to test a specific job (helps avoid checkout issues)
if [ "${3}" = "--job" ] && [ -n "${4}" ]; then
    ACT_ARGS+=("--job" "${4}")
    echo -e "${GREEN}🎯 Testing specific job: ${4}${NC}"
    echo -e "${YELLOW}💡 This skips other jobs and may avoid checkout issues${NC}"
fi


# Configure git to avoid authentication issues
# Save current git config
ORIGINAL_CREDENTIAL_HELPER=""
ORIGINAL_URL_INSTEADOF=""
if git rev-parse --git-dir > /dev/null 2>&1; then
    ORIGINAL_CREDENTIAL_HELPER=$(git config --global credential.helper 2>/dev/null || echo "")
    ORIGINAL_URL_INSTEADOF=$(git config --global --get-regexp 'url\..*\.insteadof' 2>/dev/null || echo "")

    # Temporarily disable credential helper and URL rewrites to prevent auth prompts
    git config --global credential.helper '' 2>/dev/null || true
    # Remove any URL rewrites that might cause issues
    git config --global --unset-all url.https://github.com/.insteadof 2>/dev/null || true
    git config --global --unset-all url.git@github.com:.insteadof 2>/dev/null || true

    echo -e "${GREEN}✓ Configured git to avoid authentication prompts${NC}"
fi

# Run act
echo -e "${GREEN}🚀 Running act...${NC}"
echo "Command: act ${ACT_ARGS[*]}"
echo ""

# Note about limitations
echo -e "${YELLOW}⚠️  Note: Local testing limitations:${NC}"
echo "  - AWS credentials/secrets won't work (use mocks)"
echo "  - GitHub Container Registry access limited"
echo "  - Terraform will try to run but may fail without AWS"
echo "  - Lambda deployment will fail without AWS"
echo "  - Check run creation requires GitHub App (notify job skipped by default)"
echo "  - Some steps may be skipped or mocked"
echo "  - Local composite actions require --bind flag (already added)"
echo ""
echo -e "${YELLOW}💡 Troubleshooting git authentication errors:${NC}"
echo "  - The --bind flag tells act to use local filesystem"
echo "  - Git config is disabled to prevent credential prompts"
echo "  - If errors persist, this is a known act limitation with checkout@v4"
echo ""
echo -e "${YELLOW}💡 Workaround: Test specific jobs to avoid checkout issues:${NC}"
echo "  ./scripts/test-deploy-workflow.sh ${ENVIRONMENT} \"\" --job validate"
echo ""
echo -e "${YELLOW}💡 Or test without act (faster, but less accurate):${NC}"
echo "  make ci-local  # Run equivalent shell scripts"
echo ""
echo -e "${GREEN}Press Enter to continue or Ctrl+C to cancel...${NC}"
read -r

# Run act and capture exit code
set +e  # Don't exit on error so we can restore git config
act "${ACT_ARGS[@]}"
ACT_EXIT_CODE=$?
set -e  # Re-enable exit on error

# Restore original git config if we changed it
if git rev-parse --git-dir > /dev/null 2>&1; then
    if [ -n "${ORIGINAL_CREDENTIAL_HELPER}" ]; then
        git config --global credential.helper "${ORIGINAL_CREDENTIAL_HELPER}" 2>/dev/null || true
    else
        git config --global --unset credential.helper 2>/dev/null || true
    fi

    # Restore URL rewrites if they existed
    if [ -n "${ORIGINAL_URL_INSTEADOF}" ]; then
        echo "${ORIGINAL_URL_INSTEADOF}" | while read -r line; do
            if [ -n "${line}" ]; then
                git config --global "${line%% *}" "${line#* }" 2>/dev/null || true
            fi
        done
    fi
fi

echo ""
if [ $ACT_EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}✅ Act test completed successfully${NC}"
else
    echo -e "${RED}❌ Act test completed with errors (exit code: ${ACT_EXIT_CODE})${NC}"
    echo -e "${YELLOW}💡 This is expected for local testing - many steps require AWS/GitHub access${NC}"
fi

exit $ACT_EXIT_CODE
