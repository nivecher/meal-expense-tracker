# Test Structure

This directory contains all tests for the Meal Expense Tracker application, organized to align with the app structure and follow standard testing practices.

## Directory Structure

```
tests/
├── conftest.py                    # Global test configuration and fixtures
├── README.md                      # This file
├── unit/                          # Unit tests (fast, isolated)
│   ├── app/                       # App-level tests (blueprints, config, DB)
│   │   ├── test_basic.py          # Basic app health checks
│   │   ├── test_blueprints.py     # Blueprint registration tests
│   │   ├── test_config.py         # Configuration tests
│   │   └── test_db_connection.py  # Database connection tests
│   ├── auth/                      # Authentication tests
│   │   ├── test_login.py          # Login functionality tests
│   │   └── test_login_flow.py     # Login flow tests
│   ├── expenses/                  # Expense functionality tests
│   │   ├── test_api.py            # Expense API endpoint tests
│   │   └── test_expenses.py       # Expense model/route tests
│   ├── restaurants/               # Restaurant functionality tests
│   │   ├── test_restaurant_models.py    # Restaurant model tests
│   │   ├── test_restaurant_routes.py    # Restaurant route tests
│   │   └── test_restaurant_services.py  # Restaurant service tests
│   ├── categories/                # Category functionality tests
│   │   └── test_categories.py     # Category API tests
│   ├── profile/                   # Profile functionality tests
│   │   └── test_profile.py        # Profile API tests
│   ├── main/                      # Main blueprint tests
│   │   └── test_main.py           # Main route tests
│   ├── security/                  # Security functionality tests
│   │   └── test_security.py       # Security tests
│   ├── models/                    # Shared model tests
│   └── utils/                     # Utility function tests
├── integration/                    # Integration tests (slower, with DB)
│   ├── restaurants/               # Restaurant workflow tests
│   │   └── test_restaurant_details.py  # Restaurant detail workflow
│   └── test_expense_flow.py       # Expense workflow tests
├── frontend/                      # Frontend-specific tests
│   └── unit/                      # Frontend unit tests
│       └── services/              # Frontend service tests
└── load/                          # Load testing
    └── locustfile.py              # Locust load test configuration
```

## Test Categories

### Unit Tests (`tests/unit/`)

- **Fast execution** - typically < 100ms per test
- **Isolated** - no external dependencies
- **Mocked** - external services are mocked
- **Focused** - test single function/class in isolation

### Integration Tests (`tests/integration/`)

- **Medium execution** - typically 100ms-1s per test
- **Database integration** - use test database
- **Workflow testing** - test complete user workflows
- **Real dependencies** - minimal mocking

### Load Tests (`tests/load/`)

- **Performance testing** - test system under load
- **End-to-end** - test complete user journeys
- **Scalability** - identify performance bottlenecks

## Running Tests

```bash
# Run all tests
make test

# Run specific test categories
make test-unit          # Unit tests only
make test-integration   # Integration tests only
make test-load          # Load tests only

# Run specific test files
make test-unit PYTEST_OPTS="tests/unit/app/test_blueprints.py"

# Run with coverage
make test PYTEST_OPTS="--cov=app --cov-report=html"
```

## Test Naming Conventions

- **Files**: `test_<module_name>.py`
- **Classes**: `Test<ClassName>`
- **Methods**: `test_<description>`
- **Fixtures**: `<name>_fixture`

## Best Practices

1. **Keep tests fast** - Unit tests should run in milliseconds
2. **Use descriptive names** - Test names should explain what they test
3. **One assertion per test** - Each test should verify one thing
4. **Use fixtures** - Leverage pytest fixtures for common setup
5. **Mock external services** - Don't depend on external APIs in unit tests
6. **Clean up after tests** - Ensure tests don't leave side effects
7. **Test edge cases** - Include boundary conditions and error scenarios
