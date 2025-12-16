# Branch Naming Convention

This document defines the branch naming convention for the Meal Expense Tracker project, aligned with our Conventional Commits standard.

## Branch Naming Format

Branches should follow this format:

```
<type>/<description>
```

Where:

- `<type>` is one of the Conventional Commits types (see below)
- `<description>` is a short, kebab-case description of the change

## Allowed Types

Based on our Conventional Commits configuration, the following types are allowed:

- **feat**: New feature
- **fix**: Bug fix
- **docs**: Documentation changes
- **style**: Code style changes (formatting, etc.)
- **refactor**: Code refactoring
- **test**: Adding or modifying tests
- **chore**: Build process or auxiliary tool changes
- **ci**: CI/CD related changes
- **perf**: Performance improvements
- **revert**: Revert a previous commit
- **wip**: Work in progress (temporary branches)

## Protected Branches

The following branches are protected and should not be used for feature work:

- `main` - Production branch
- `develop` - Development branch (if used)

## Examples

### ✅ Good Branch Names

```
feat/add-expense-filtering
fix/restaurant-search-bug
docs/update-api-documentation
style/format-expense-list
refactor/simplify-auth-logic
test/add-integration-tests
chore/update-dependencies
ci/add-branch-validation
perf/optimize-database-queries
revert/remove-broken-feature
wip/experimental-ui-changes
```

### ❌ Bad Branch Names

```
feature/add-filtering          # Use 'feat' not 'feature'
bugfix/search-issue            # Use 'fix' not 'bugfix'
my-feature                     # Missing type prefix
feat/AddExpenseFiltering       # Should be kebab-case
feat/add expense filtering     # No spaces allowed
feat/add-expense-filtering-v2  # Avoid version numbers
```

## Description Guidelines

1. **Use kebab-case**: All lowercase with hyphens
2. **Be descriptive but concise**: 2-4 words typically
3. **Focus on what, not why**: Describe the change, not the reason
4. **No special characters**: Only letters, numbers, and hyphens
5. **No version numbers**: Avoid v1, v2, etc. in branch names

## Enforcement

Branch naming is enforced through:

1. **Pre-push hook**: Validates branch names before pushing to remote
2. **CI workflow**: Checks branch names on pull requests
3. **Manual validation**: Script available at `scripts/validate_branch.py`

## Override (Emergency Only)

If you need to bypass validation temporarily (e.g., hotfix), you can:

```bash
# Skip pre-push hook (not recommended)
git push --no-verify

# Or use a valid type prefix even for urgent fixes
fix/critical-security-patch
```

## Related Documentation

- [Conventional Commits](https://www.conventionalcommits.org/)
- [Contributing Guide](../CONTRIBUTING.md)
- [Technology Stack](./TECHNOLOGY.md)
