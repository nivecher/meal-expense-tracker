# Playwright Tests

This directory contains end-to-end tests using Playwright for the Meal Expense Tracker application.

## Test Files

- `console-tests.spec.js` - Tests browser console for errors and warnings
- `security-headers.spec.js` - Tests security headers configuration
- `user-flows.spec.js` - Comprehensive user flow and usability tests

## Running Tests

### Prerequisites

1. Install Playwright:
   ```bash
   npm install @playwright/test
   npx playwright install
   ```

2. Setup test user (required for user flow tests):
   ```bash
   make setup-test-user
   # or
   python scripts/setup_test_user.py
   ```

3. Start your Flask application:
   ```bash
   make run
   # or
   python wsgi.py
   ```

### Run All Tests

```bash
npx playwright test
```

### Run Using Makefile (Recommended)

```bash
# User flow tests (automatically sets up test user)
make test-user-flows

# User flow tests with visible browser
make test-user-flows-headed

# All frontend tests
make test-e2e

# Console tests
make test-console

# Security headers tests
make test-security
```

### Run Specific Test File

```bash
# Console tests
npx playwright test console-tests.spec.js

# Security headers tests
npx playwright test security-headers.spec.js

# User flow tests
npx playwright test user-flows.spec.js
```

### Run with Different Base URL

```bash
BASE_URL=http://localhost:5000 npx playwright test
```

### Run in Headed Mode (see browser)

```bash
npx playwright test --headed
```

### Run in Debug Mode

```bash
npx playwright test --debug
```

## Test Configuration

Tests use the following configuration:
- Base URL: `http://localhost:5000` (configurable via `BASE_URL` env var)
- Timeout: 30 seconds
- Retries: 2 (for console tests)

## What Tests Cover

### Console Tests
- Browser console errors and warnings
- JavaScript syntax errors
- Network errors
- Performance issues
- Module loading errors

### Security Headers Tests
- X-Content-Type-Options header
- Referrer-Policy header
- X-Frame-Options header
- Content-Security-Policy configuration
- Cache-Control headers
- Content-Type headers with proper charset
- Absence of deprecated headers (Expires, Pragma)

### User Flow Tests
- Authentication flows (login, logout, registration, password change)
- Expense management (add, edit, delete, list, filter, search)
- Restaurant management (add, edit, delete, search)
- Navigation and page transitions
- Form validation and error handling
- Mobile responsiveness
- Accessibility (keyboard navigation, form labels)
- Performance (page load times, task completion times)
- Loading states and user feedback

## Test Data

Tests use the following test user:
- Username: `testuser_1`
- Password: `testpass`

Make sure this user exists in your test database.
