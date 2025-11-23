# Playwright Tests

This directory contains end-to-end tests using Playwright for the Meal Expense Tracker application.

## Test Files

- `console-tests.spec.js` - Tests browser console for errors and warnings
- `security-headers.spec.js` - Tests security headers configuration

## Running Tests

### Prerequisites

1. Install Playwright:
   ```bash
   npm install @playwright/test
   npx playwright install
   ```

2. Start your Flask application:
   ```bash
   python app.py
   ```

### Run All Tests

```bash
npx playwright test
```

### Run Specific Test File

```bash
# Console tests
npx playwright test console-tests.spec.js

# Security headers tests
npx playwright test security-headers.spec.js
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

## Test Data

Tests use the following test user:
- Username: `testuser_1`
- Password: `testpass`

Make sure this user exists in your test database.
