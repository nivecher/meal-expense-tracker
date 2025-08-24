# Cursor Rules for Spec-Driven Development

This directory contains comprehensive Cursor rules that implement the development standards and best practices for the Meal Expense Tracker project.

These rules are designed to guide development according to the TIGER principles and ensure consistent, high-quality code.

## Rule Files Overview

### Core Development Principles

- **`tiger-principles.mdc`** - TIGER methodology (Testable, Incremental, Goal-oriented, Explicit, Responsibility-focused)
- **`development-workflow.mdc`** - Git workflow, branching strategy, and development processes

### Language-Specific Standards

- **`python-flask-standards.mdc`** - Python and Flask development standards
- **`javascript-standards.mdc`** - JavaScript development and organization standards
- **`terraform-standards.mdc`** - Infrastructure as Code standards

### Quality and Security

- **`testing-standards.mdc`** - Testing best practices and coverage requirements
- **`security-standards.mdc`** - Security guidelines and best practices
- **`api-design-standards.mdc`** - API design principles and RESTful standards

### Application Specifications

- **`app-requirements.mdc`** - Core application requirements and business rules
- **`feature-specs.mdc`** - Feature specifications and user stories
- **`data-models.mdc`** - Data models and database schema specifications
- **`ui-ux-specs.mdc`** - UI/UX specifications and design requirements

### Technology-Specific

- **`my-google-rules.mdc`** - Google Maps API integration standards

## How to Use These Rules

### For Developers

1. **Always Apply Rules**: Most rules are set to `alwaysApply: true` to ensure consistent development
2. **Language-Specific Application**: Rules automatically apply to relevant file types (e.g., Python rules for `.py` files)
3. **Context-Aware Guidance**: Rules provide specific guidance based on the type of code being written
4. **Specification Reference**: Use app requirements and feature specs to understand what to build
5. **Data Model Guidance**: Reference data models for database structure and relationships

### For Code Review

1. **Use as Checklist**: Reference these rules during code reviews
2. **Enforce Standards**: Ensure all code follows the established patterns
3. **Continuous Improvement**: Update rules based on lessons learned

### For New Team Members

1. **Learning Resource**: Study these rules to understand project standards
2. **Onboarding Guide**: Use as a reference for development practices
3. **Best Practices**: Learn from established patterns and conventions

## TIGER Principles in Action

### T - Testable

- All code must be written with testing in mind
- Use dependency injection and pure functions
- Aim for 80%+ test coverage

### I - Incremental

- Make small, focused changes
- Use feature flags for large rollouts
- Continuous integration and deployment

### G - Goal-oriented

- Each function has a single responsibility
- Code solves specific business problems
- Regular alignment with business objectives

### E - Explicit

- Clear naming conventions
- Type hints and documentation
- Explicit error handling

### R - Responsibility-focused

- Separation of concerns
- Clear layer boundaries
- Focused, maintainable code

## Technology Stack Standards

### Backend (Python/Flask)

- Python 3.13+ with type hints
- Flask 3.1.1 with blueprint architecture
- SQLAlchemy 2.0 syntax
- Pytest for testing

### Frontend (JavaScript)

- ES6+ syntax
- External JavaScript files only
- Modern browser APIs
- Accessibility best practices

### Infrastructure (Terraform)

- Anton Babenko best practices
- Modular, reusable code
- Security-first approach
- Environment separation

## Quality Gates

All code must pass these quality checks:

- ✅ Linting (Black, flake8, ESLint)
- ✅ Type checking (mypy)
- ✅ Security scanning (Bandit, Trivy)
- ✅ Test coverage (80%+)
- ✅ Code review approval
- ✅ Automated testing

## Contributing to Rules

1. **Identify Gaps**: Note areas where rules could be improved
2. **Propose Changes**: Submit suggestions for rule updates
3. **Document Decisions**: Update rules based on team decisions
4. **Keep Current**: Ensure rules reflect current best practices

## Related Documentation

- **`docs/CODING_GUIDELINES.md`** - Detailed coding standards
- **`docs/DEVELOPMENT.md`** - Development environment setup
- **`docs/TECHNOLOGY.md`** - Technology stack decisions
- **`.windsurf/`** - Windsurf rules and knowledge base

## Specification-Driven Development

These Cursor rules now provide a complete framework for specification-driven development:

1. **What to Build**: Application requirements and feature specifications
2. **How to Build**: Coding standards and technical guidelines
3. **What it Looks Like**: UI/UX specifications and design requirements
4. **How it Works**: Data models and business logic specifications
5. **How to Test**: Testing standards and quality requirements

This approach ensures that development is guided by clear specifications while maintaining high code quality standards.

---

_These rules are living documents that evolve with the project. Regular review and updates ensure they remain relevant and effective._
