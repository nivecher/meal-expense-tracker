# Coding Guidelines for Meal Expense Tracker

## Table of Contents

1. [TIGER Principles](#tiger-principles)
2. [Technology Stack](#technology-stack)
3. [Python/Flask Guidelines](#pythonflask-guidelines)
4. [JavaScript Guidelines](#javascript-guidelines)
5. [Testing Guidelines](#testing-guidelines)
6. [Security Guidelines](#security-guidelines)
7. [Git Workflow](#git-workflow)
8. [Documentation](#documentation)

## TIGER Principles

### T - Testable

- Write code that is easy to test in isolation
- Follow the Arrange-Act-Assert pattern in tests
- Use dependency injection for external services
- Keep business logic pure and side-effect free when possible
- Write unit tests for all public methods and functions
- Use test doubles (mocks, stubs, fakes) for external dependencies
- Aim for high test coverage of business logic
- Test edge cases and error conditions

### I - Incremental

- Make small, focused changes
- Each commit should be a single logical change
- Use feature flags for large feature rollouts
- Break down large features into smaller, deliverable pieces
- Continuously integrate and deploy small changes
- Use iterative development with frequent feedback loops
- Refactor in small, safe steps

### G - Goal-oriented

- Each function/method should have a single responsibility
- Code should be written to solve specific business problems
- Avoid premature optimization
- Document the "why" behind important decisions
- Align code structure with business domains
- Regularly review and align code with business objectives
- Remove unused code and dead features

### E - Explicit

- Make dependencies explicit
- Use clear, descriptive names for variables, functions, and classes
- Avoid magic numbers and strings - use named constants
- Make type contracts explicit with type hints
- Document complex algorithms and business rules
- Make error conditions and edge cases explicit
- Prefer explicit over implicit behavior

### R - Responsibility-focused

- Follow the Single Responsibility Principle
- Group related functionality together
- Separate concerns between layers (presentation, business logic, data access)
- Use appropriate design patterns for clear responsibility separation
- Keep functions and classes focused on one thing
- Avoid god objects and utility classes
- Design for change by isolating volatile components

## Technology Stack

### Backend

- Python 3.13
- Flask 3.1.1
- SQLAlchemy 2.0
- Pytest for testing
- Gunicorn for production WSGI server

### Frontend

- Modern JavaScript (ES6+)
- HTML5 / CSS3
- Bootstrap 5 for styling
- jQuery for DOM manipulation
- Webpack for asset bundling

### Infrastructure

- AWS (EC2, RDS, S3, Lambda)
- Terraform for infrastructure as code
- Docker for containerization
- GitHub Actions for CI/CD

## Python/Flask Guidelines

### Project Structure

```
app/
  ├── api/              # API endpoints and resources
  ├── auth/             # Authentication and user management
  ├── expenses/         # Expense tracking functionality
  ├── restaurants/      # Restaurant management
  ├── services/         # Business logic and services
  ├── static/           # Static files (JS, CSS, images)
  ├── templates/        # Jinja2 templates
  └── utils/            # Utility functions and helpers

```

### Code Style

- Follow [PEP 8](https://www.python.org/dev/peps/pep-0008/)
- Use type hints for all function signatures
- Maximum line length: 120 characters (Black default)
- Use double quotes for strings
- Use absolute imports
- Use `snake_case` for variables and functions
- Use `PascalCase` for classes
- Use `UPPER_CASE` for constants

### Best Practices

- Keep route handlers thin
- Move business logic to service layer
- Use SQLAlchemy for database operations
- Implement proper error handling
- Use logging appropriately
- Follow RESTful API design principles
- Use environment variables for configuration
- Implement proper input validation

## JavaScript Guidelines

### Code Style (2)

- Use ES6+ syntax
- Use `camelCase` for variables and functions
- Use `PascalCase` for React components
- Use `UPPER_CASE` for constants
- Use template literals for string interpolation
- Use destructuring for objects and arrays
- Use arrow functions for callbacks

### Best Practices (2)

- No inline JavaScript in HTML files
- Use modules for code organization
- Keep DOM manipulation separate from business logic
- Use event delegation for dynamic content
- Implement proper error handling
- Use modern browser APIs and features
- Follow accessibility best practices

## Testing Guidelines

### Unit Tests

- Test one thing per test case
- Use descriptive test names
- Follow Arrange-Act-Assert pattern
- Use fixtures for test data
- Mock external dependencies
- Test edge cases and error conditions

### Integration Tests

- Test API endpoints
- Test database interactions
- Test authentication and authorization
- Test error responses

### Test Coverage

- Aim for 80%+ test coverage
- Cover all business logic
- Test error conditions
- Test edge cases

## Security Guidelines

### Authentication & Authorization

- Use secure password hashing (bcrypt)
- Implement proper session management
- Use CSRF protection
- Implement rate limiting
- Use secure HTTP headers

### Data Protection

<!-- markdownlint-disable MD044 -->

- Use HTTPS everywhere
- Sanitize all user inputs
- Use parameterized queries
- Encrypt sensitive data at rest
- Implement proper access controls

### Dependencies

- Keep dependencies up to date
- Use dependency scanning
- Pin dependency versions
- Review third-party code

## Git Workflow

### Branching Strategy

- Use feature branches
- Follow semantic versioning
- Use meaningful branch names
- Keep branches up to date with main

### Commit Messages

- Use present tense
- Start with a capital letter
- Keep the first line under 50 characters
- Include a blank line between subject and body
- Reference issue numbers when applicable

### Code Review

- Review your own code first
- Be constructive in feedback
- Keep PRs small and focused
- Address all feedback before merging

## Documentation

### Code Comments

- Document why, not what
- Keep comments up to date
- Remove commented-out code
- Use docstrings for public APIs

### API Documentation

- Document all endpoints
- Include request/response examples
- Document error responses
- Keep documentation up to date

### Project Documentation

- Keep README up to date
- Document setup and deployment
- Document environment variables
- Keep architecture decisions documented

## Code Quality Tools

### Python

- Black for code formatting
- isort for import sorting
- flake8 for linting
- mypy for type checking
- bandit for security scanning

### JavaScript

- ESLint for linting
- Prettier for code formatting
- Jest for testing
- Webpack for bundling

## Performance Guidelines

### Backend (2)

- Optimize database queries
- Use caching where appropriate
- Implement pagination for large datasets
- Use asynchronous processing for long-running tasks

### Frontend (2)

- Minimize bundle size
- Lazy load components
- Optimize images
- Implement proper caching

## Error Handling

### Backend (3)

- Use appropriate HTTP status codes
- Provide meaningful error messages
- Log errors with context
- Implement proper exception handling

### Frontend (3)

- Handle API errors gracefully
- Show user-friendly error messages
- Implement retry logic for failed requests
- Log errors for debugging

## Monitoring and Logging

### Backend (4)

- Use structured logging
- Include request IDs in logs
- Log errors with stack traces
- Monitor application metrics

### Frontend (4)

- Log JavaScript errors
- Track user interactions
- Monitor performance metrics
- Implement analytics

## Deployment

### Development

- Use local development environment
- Keep environment variables in .env file
- Document setup process

### Staging

- Mirror production environment
- Test all features before production
- Use feature flags for gradual rollouts

### Production

- Use blue-green deployments
- Monitor application health
- Implement rollback procedures
- Keep backups

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Write tests
5. Update documentation
6. Submit a pull request

## License

[Specify your license here]

---

_Last updated: July 17, 2025_
