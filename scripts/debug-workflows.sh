#!/bin/bash
# Debug GitHub Actions workflow failures
# This script validates workflows and identifies common issues

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

LOG_FILE="/home/mtd37/workspace/meal-expense-tracker/.cursor/debug.log"
SESSION_ID="debug-workflows-$(date +%s)"

# Logging function
log() {
    local level=$1
    shift
    local message="$@"
    local timestamp=$(date +%s%3N)
    echo "{\"id\":\"log_${timestamp}_$$\",\"timestamp\":${timestamp},\"location\":\"debug-workflows.sh:${BASH_LINENO[0]}\",\"message\":\"${message}\",\"data\":{\"level\":\"${level}\",\"sessionId\":\"${SESSION_ID}\"},\"sessionId\":\"${SESSION_ID}\",\"runId\":\"run1\",\"hypothesisId\":\"A\"}" >> "$LOG_FILE"
    echo -e "${message}"
}

log "INFO" "Starting workflow debugging..."

# Check Python availability
if ! command -v python3 &> /dev/null; then
    log "ERROR" "${RED}❌ Python3 not found${NC}"
    exit 1
fi

WORKFLOWS_DIR=".github/workflows"
REUSABLE_DIR=".github/workflows/reusable"
ACTIONS_DIR=".github/actions"

# Hypothesis A: Missing reusable workflow files
log "INFO" "${BLUE}=== Hypothesis A: Checking for missing reusable workflows ===${NC}"
MISSING_REUSABLE=0
REUSABLE_REFERENCES_FOUND=0

# Check for referenced reusable workflows first
for workflow in ci.yml deploy.yml release.yml test.yml tag.yml codeql.yml; do
    if [ -f "${WORKFLOWS_DIR}/${workflow}" ]; then
        log "INFO" "Checking ${workflow} for reusable workflow references..."
        while IFS= read -r line; do
            if [[ "$line" =~ uses:.*reusable/ ]]; then
                REUSABLE_REFERENCES_FOUND=1
                REF_PATH=$(echo "$line" | sed -E 's/.*uses:\s*\.\/\.github\/workflows\/reusable\/([^[:space:]]+).*/\1/')
                if [ ! -d "$REUSABLE_DIR" ] || [ ! -f "${REUSABLE_DIR}/${REF_PATH}" ]; then
                    log "ERROR" "${RED}❌ Missing reusable workflow: ${REUSABLE_DIR}/${REF_PATH} (referenced in ${workflow})${NC}"
                    MISSING_REUSABLE=1
                else
                    log "INFO" "${GREEN}✓ Found reusable workflow: ${REF_PATH}${NC}"
                fi
            fi
        done < "${WORKFLOWS_DIR}/${workflow}"
    fi
done

# Only report missing directory if workflows actually reference reusable workflows
if [ $REUSABLE_REFERENCES_FOUND -eq 0 ]; then
    log "INFO" "${GREEN}✓ No reusable workflow references found (following project philosophy)${NC}"
    log "INFO" "${GREEN}Hypothesis A: REJECTED - No reusable workflows needed${NC}"
elif [ $MISSING_REUSABLE -eq 1 ]; then
    log "ERROR" "${RED}Hypothesis A: CONFIRMED - Missing reusable workflow files${NC}"
else
    log "INFO" "${GREEN}Hypothesis A: REJECTED - All reusable workflows found${NC}"
fi

# Hypothesis B: Invalid YAML syntax
log "INFO" "${BLUE}=== Hypothesis B: Checking YAML syntax ===${NC}"
YAML_ERRORS=0

for workflow_file in "${WORKFLOWS_DIR}"/*.yml; do
    if [ -f "$workflow_file" ]; then
        log "INFO" "Validating YAML syntax: $(basename $workflow_file)"
        if python3 -c "import yaml; yaml.safe_load(open('$workflow_file'))" 2>/dev/null; then
            log "INFO" "${GREEN}✓ $(basename $workflow_file) - Valid YAML${NC}"
        else
            log "ERROR" "${RED}❌ $(basename $workflow_file) - YAML syntax error${NC}"
            python3 -c "import yaml; yaml.safe_load(open('$workflow_file'))" 2>&1 | head -5
            YAML_ERRORS=1
        fi
    fi
done

if [ $YAML_ERRORS -eq 1 ]; then
    log "ERROR" "${RED}Hypothesis B: CONFIRMED - YAML syntax errors found${NC}"
else
    log "INFO" "${GREEN}Hypothesis B: REJECTED - All YAML files are valid${NC}"
fi

# Hypothesis C: Missing custom action files
log "INFO" "${BLUE}=== Hypothesis C: Checking custom action references ===${NC}"
MISSING_ACTIONS=0

for workflow_file in "${WORKFLOWS_DIR}"/*.yml; do
    if [ -f "$workflow_file" ]; then
        log "INFO" "Checking $(basename $workflow_file) for custom action references..."
        while IFS= read -r line; do
            if [[ "$line" =~ uses:\s*\.\/\.github/actions/ ]]; then
                ACTION_PATH=$(echo "$line" | sed -E 's/.*uses:\s*\.\/\.github\/actions\/([^[:space:]]+).*/\1/')
                ACTION_DIR="${ACTIONS_DIR}/${ACTION_PATH}"
                if [ ! -d "$ACTION_DIR" ] || [ ! -f "${ACTION_DIR}/action.yml" ]; then
                    log "ERROR" "${RED}❌ Missing action: ${ACTION_DIR} (referenced in $(basename $workflow_file))${NC}"
                    MISSING_ACTIONS=1
                else
                    log "INFO" "${GREEN}✓ Found action: ${ACTION_PATH}${NC}"
                fi
            fi
        done < "$workflow_file"
    fi
done

if [ $MISSING_ACTIONS -eq 1 ]; then
    log "ERROR" "${RED}Hypothesis C: CONFIRMED - Missing custom action files${NC}"
else
    log "INFO" "${GREEN}Hypothesis C: REJECTED - All custom actions found${NC}"
fi

# Hypothesis D: Invalid action.yml syntax
log "INFO" "${BLUE}=== Hypothesis D: Validating action.yml files ===${NC}"
ACTION_YAML_ERRORS=0

if [ -d "$ACTIONS_DIR" ]; then
    find "$ACTIONS_DIR" -name "action.yml" | while read -r action_file; do
        log "INFO" "Validating: $action_file"
        if python3 -c "import yaml; yaml.safe_load(open('$action_file'))" 2>/dev/null; then
            log "INFO" "${GREEN}✓ $(basename $(dirname $action_file)) - Valid action.yml${NC}"
        else
            log "ERROR" "${RED}❌ $action_file - Invalid YAML${NC}"
            python3 -c "import yaml; yaml.safe_load(open('$action_file'))" 2>&1 | head -5
            ACTION_YAML_ERRORS=1
        fi
    done
fi

if [ $ACTION_YAML_ERRORS -eq 1 ]; then
    log "ERROR" "${RED}Hypothesis D: CONFIRMED - Invalid action.yml files${NC}"
else
    log "INFO" "${GREEN}Hypothesis D: REJECTED - All action.yml files are valid${NC}"
fi

# Hypothesis E: Workflow dependency issues
log "INFO" "${BLUE}=== Hypothesis E: Checking workflow dependencies ===${NC}"
DEPENDENCY_ISSUES=0

# Check workflow_run triggers
for workflow_file in "${WORKFLOWS_DIR}"/*.yml; do
    if [ -f "$workflow_file" ]; then
        if grep -q "workflow_run:" "$workflow_file"; then
            WORKFLOW_NAME=$(grep "^name:" "$workflow_file" | head -1 | sed 's/name: *//' | tr -d '"' | tr -d "'")
            REFERENCED_WORKFLOW=$(grep -A 2 "workflow_run:" "$workflow_file" | grep "workflows:" | sed -E 's/.*workflows:\s*\[([^]]+)\].*/\1/' | tr -d '"' | tr -d "'")

            if [ -n "$REFERENCED_WORKFLOW" ]; then
                REFERENCED_FILE=$(find "${WORKFLOWS_DIR}" -name "*.yml" -exec grep -l "^name:.*${REFERENCED_WORKFLOW}" {} \; | head -1)
                if [ -z "$REFERENCED_FILE" ]; then
                    log "ERROR" "${RED}❌ Workflow '${WORKFLOW_NAME}' references non-existent workflow: ${REFERENCED_WORKFLOW}${NC}"
                    DEPENDENCY_ISSUES=1
                else
                    log "INFO" "${GREEN}✓ Workflow dependency valid: ${WORKFLOW_NAME} -> ${REFERENCED_WORKFLOW}${NC}"
                fi
            fi
        fi
    fi
done

if [ $DEPENDENCY_ISSUES -eq 1 ]; then
    log "ERROR" "${RED}Hypothesis E: CONFIRMED - Workflow dependency issues${NC}"
else
    log "INFO" "${GREEN}Hypothesis E: REJECTED - All workflow dependencies valid${NC}"
fi

# Summary
log "INFO" "${BLUE}=== Summary ===${NC}"
TOTAL_ISSUES=$((MISSING_REUSABLE + YAML_ERRORS + MISSING_ACTIONS + ACTION_YAML_ERRORS + DEPENDENCY_ISSUES))

if [ $TOTAL_ISSUES -eq 0 ]; then
    log "INFO" "${GREEN}✅ No workflow issues detected${NC}"
    log "INFO" "All hypotheses rejected. Workflows appear to be syntactically correct."
    log "INFO" "If workflows are still failing, check:"
    log "INFO" "  1. GitHub Actions logs for runtime errors"
    log "INFO" "  2. Required secrets and environment variables"
    log "INFO" "  3. AWS credentials and permissions"
    log "INFO" "  4. External service availability"
    exit 0
else
    log "ERROR" "${RED}❌ Found ${TOTAL_ISSUES} issue(s)${NC}"
    log "ERROR" "Please fix the issues above and re-run this script"
    exit 1
fi
