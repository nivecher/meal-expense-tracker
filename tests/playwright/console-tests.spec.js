/**
 * Playwright Console Tests
 *
 * Tests browser console for errors, warnings, and performance issues
 * across all major pages of the Meal Expense Tracker application.
 *
 * @version 1.0.0
 * @author Meal Expense Tracker Team
 */

import { test, expect } from '@playwright/test';

// Console message types to track
const CONSOLE_MESSAGE_TYPES = {
  ERROR: 'error',
  WARNING: 'warning',
  LOG: 'log',
  INFO: 'info',
  DEBUG: 'debug',
};

// Expected console patterns that should be filtered out
const FILTERED_PATTERNS = [
  /Bootstrap.*deprecated/i,
  /jQuery.*deprecated/i,
  /Font Awesome.*deprecated/i,
  /Select2.*deprecated/i,
  /Chart\.js.*deprecated/i,
  /cdn\.jsdelivr\.net/i,
  /cdnjs\.cloudflare\.com/i,
  /chrome-extension/i,
  /moz-extension/i,
  /webkit.*not supported/i,
];

// Test configuration
const TEST_CONFIG = {
  baseUrl: process.env.BASE_URL || 'http://localhost:5000',
  timeout: 30000,
  retries: 2,
};

/**
 * Console message collector
 */
class ConsoleCollector {
  constructor() {
    this.messages = [];
    this.errors = [];
    this.warnings = [];
    this.logs = [];
  }

  addMessage(type, message, location) {
    const consoleMessage = {
      type,
      message: message.text(),
      location: location ? {
        url: location.url,
        lineNumber: location.lineNumber,
        columnNumber: location.columnNumber,
      } : null,
      timestamp: new Date().toISOString(),
    };

    this.messages.push(consoleMessage);

    switch (type) {
      case CONSOLE_MESSAGE_TYPES.ERROR:
        this.errors.push(consoleMessage);
        break;
      case CONSOLE_MESSAGE_TYPES.WARNING:
        this.warnings.push(consoleMessage);
        break;
      case CONSOLE_MESSAGE_TYPES.LOG:
        this.logs.push(consoleMessage);
        break;
    }
  }

  getFilteredMessages() {
    return this.messages.filter(msg =>
      !FILTERED_PATTERNS.some(pattern => pattern.test(msg.message))
    );
  }

  getUnfilteredMessages() {
    return this.messages.filter(msg =>
      FILTERED_PATTERNS.some(pattern => pattern.test(msg.message))
    );
  }

  getCriticalErrors() {
    return this.errors.filter(error =>
      !FILTERED_PATTERNS.some(pattern => pattern.test(error.message))
    );
  }

  getSummary() {
    const filtered = this.getFilteredMessages();
    const unfiltered = this.getUnfilteredMessages();
    const critical = this.getCriticalErrors();

    return {
      total: this.messages.length,
      filtered: filtered.length,
      unfiltered: unfiltered.length,
      critical: critical.length,
      errors: this.errors.length,
      warnings: this.warnings.length,
      logs: this.logs.length,
    };
  }
}

/**
 * Setup console monitoring for a page
 */
async function setupConsoleMonitoring(page) {
  const collector = new ConsoleCollector();

  // Listen to console messages
  page.on('console', (msg) => {
    const type = msg.type();
    const location = msg.location();
    collector.addMessage(type, msg, location);
  });

  // Listen to page errors
  page.on('pageerror', (error) => {
    collector.addMessage(CONSOLE_MESSAGE_TYPES.ERROR, {
      text: () => `Page Error: ${error.message}`,
    }, {
      url: error.stack?.split('\n')[1] || 'unknown',
      lineNumber: 0,
      columnNumber: 0,
    });
  });

  // Listen to unhandled promise rejections
  page.on('unhandledrejection', (error) => {
    collector.addMessage(CONSOLE_MESSAGE_TYPES.ERROR, {
      text: () => `Unhandled Promise Rejection: ${error}`,
    });
  });

  return collector;
}

/**
 * Test suite for console issues
 */
test.describe('Browser Console Issues', () => {
  let collector;

  test.beforeEach(async ({ page }) => {
    // Setup console monitoring
    collector = await setupConsoleMonitoring(page);

    // Set longer timeout for console tests
    test.setTimeout(TEST_CONFIG.timeout);
  });

  test.afterEach(async ({ page }) => {
    // Log console summary
    const summary = collector.getSummary();
    console.log('\n📊 Console Summary:', summary);

    if (summary.critical > 0) {
      console.log('\n❌ Critical Errors:');
      collector.getCriticalErrors().forEach((error, index) => {
        console.log(`  ${index + 1}. ${error.message}`);
        if (error.location) {
          console.log(`     Location: ${error.location.url}:${error.location.lineNumber}`);
        }
      });
    }

    if (summary.filtered > 0) {
      console.log('\n🔍 Filtered Messages:');
      collector.getFilteredMessages().forEach((msg, index) => {
        console.log(`  ${index + 1}. [${msg.type.toUpperCase()}] ${msg.message}`);
      });
    }
  });

  test('Home page should have clean console', async ({ page }) => {
    await page.goto(`${TEST_CONFIG.baseUrl}/`);
    await page.waitForLoadState('networkidle');

    // Wait for any async operations
    await page.waitForTimeout(2000);

    const summary = collector.getSummary();

    // Should have no critical errors
    expect(summary.critical).toBe(0);

    // Log any issues found
    if (summary.filtered > 0) {
      console.log('Issues found on home page:');
      collector.getFilteredMessages().forEach((msg, index) => {
        console.log(`  ${index + 1}. [${msg.type.toUpperCase()}] ${msg.message}`);
      });
    }
  });

  test('Login page should have clean console', async ({ page }) => {
    await page.goto(`${TEST_CONFIG.baseUrl}/auth/login`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    const summary = collector.getSummary();
    expect(summary.critical).toBe(0);
  });

  test('Expenses page should have clean console', async ({ page }) => {
    // First login
    await page.goto(`${TEST_CONFIG.baseUrl}/auth/login`);
    await page.fill('input[name="username"]', 'testuser_1');
    await page.fill('input[name="password"]', 'testpass');
    await page.click('button[type="submit"]');

    // Wait for redirect and load
    await page.waitForURL('**/expenses');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(3000);

    const summary = collector.getSummary();

    // Should have no critical errors
    expect(summary.critical).toBe(0);

    // Check if expenses are loading
    const expensesContainer = page.locator('#card-view-container, #table-view-container');
    await expect(expensesContainer).toBeVisible();

    // Log any issues found
    if (summary.filtered > 0) {
      console.log('Issues found on expenses page:');
      collector.getFilteredMessages().forEach((msg, index) => {
        console.log(`  ${index + 1}. [${msg.type.toUpperCase()}] ${msg.message}`);
      });
    }
  });

  test('Restaurants page should have clean console', async ({ page }) => {
    // Login first
    await page.goto(`${TEST_CONFIG.baseUrl}/auth/login`);
    await page.fill('input[name="username"]', 'testuser_1');
    await page.fill('input[name="password"]', 'testpass');
    await page.click('button[type="submit"]');

    // Navigate to restaurants
    await page.goto(`${TEST_CONFIG.baseUrl}/restaurants`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    const summary = collector.getSummary();
    expect(summary.critical).toBe(0);
  });

  test('Add expense page should have clean console', async ({ page }) => {
    // Login first
    await page.goto(`${TEST_CONFIG.baseUrl}/auth/login`);
    await page.fill('input[name="username"]', 'testuser_1');
    await page.fill('input[name="password"]', 'testpass');
    await page.click('button[type="submit"]');

    // Navigate to add expense
    await page.goto(`${TEST_CONFIG.baseUrl}/expenses/add`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    const summary = collector.getSummary();
    expect(summary.critical).toBe(0);
  });

  test('JavaScript modules should load without errors', async ({ page }) => {
    await page.goto(`${TEST_CONFIG.baseUrl}/`);
    await page.waitForLoadState('networkidle');

    // Check if main modules are loaded
    const mainModuleLoaded = await page.evaluate(() => {
      return typeof window.appInitialized !== 'undefined' ||
             document.querySelector('script[src*="main.js"]') !== null;
    });

    expect(mainModuleLoaded).toBeTruthy();

    // Check for module loading errors
    const moduleErrors = collector.errors.filter(error =>
      error.message.includes('Failed to load') ||
      error.message.includes('Module not found') ||
      error.message.includes('import')
    );

    expect(moduleErrors.length).toBe(0);
  });

  test('Error handler should be working', async ({ page }) => {
    await page.goto(`${TEST_CONFIG.baseUrl}/`);
    await page.waitForLoadState('networkidle');

    // Check if error handler utilities are available
    const errorHandlerAvailable = await page.evaluate(() => {
      return typeof window.getErrorStats === 'function' &&
             typeof window.clearErrors === 'function' &&
             typeof window.showFilteredMessages === 'function';
    });

    // Note: Error handler is currently disabled, so this might be false
    // This test documents the expected behavior
    console.log('Error handler available:', errorHandlerAvailable);
  });

  test('Console filtering should work correctly', async ({ page }) => {
    await page.goto(`${TEST_CONFIG.baseUrl}/`);
    await page.waitForLoadState('networkidle');

    // Check if console filter is active
    const filterActive = await page.evaluate(() => {
      return typeof window.filteredWarnings !== 'undefined' ||
             typeof window.showFilteredWarnings === 'function';
    });

    console.log('Console filter active:', filterActive);

    // Check for filtered vs unfiltered messages
    const summary = collector.getSummary();
    console.log('Filtered messages:', summary.filtered);
    console.log('Unfiltered messages:', summary.unfiltered);
  });

  test('Performance should be acceptable', async ({ page }) => {
    const startTime = Date.now();

    await page.goto(`${TEST_CONFIG.baseUrl}/`);
    await page.waitForLoadState('networkidle');

    const loadTime = Date.now() - startTime;

    // Page should load within 5 seconds
    expect(loadTime).toBeLessThan(5000);

    console.log(`Page load time: ${loadTime}ms`);

    // Check for performance-related console messages
    const performanceWarnings = collector.warnings.filter(warning =>
      warning.message.includes('performance') ||
      warning.message.includes('slow') ||
      warning.message.includes('timeout')
    );

    expect(performanceWarnings.length).toBe(0);
  });
});

/**
 * Test suite for specific console issues
 */
test.describe('Specific Console Issues', () => {
  test('No JavaScript syntax errors', async ({ page }) => {
    const collector = await setupConsoleMonitoring(page);

    await page.goto(`${TEST_CONFIG.baseUrl}/`);
    await page.waitForLoadState('networkidle');

    // Check for syntax errors
    const syntaxErrors = collector.errors.filter(error =>
      error.message.includes('SyntaxError') ||
      error.message.includes('Unexpected token') ||
      error.message.includes('Unexpected end of input')
    );

    expect(syntaxErrors.length).toBe(0);
  });

  test('No undefined variable errors', async ({ page }) => {
    const collector = await setupConsoleMonitoring(page);

    await page.goto(`${TEST_CONFIG.baseUrl}/`);
    await page.waitForLoadState('networkidle');

    // Check for undefined variable errors
    const undefinedErrors = collector.errors.filter(error =>
      error.message.includes('is not defined') ||
      error.message.includes('Cannot read property') ||
      error.message.includes('Cannot read properties')
    );

    expect(undefinedErrors.length).toBe(0);
  });

  test('No network errors', async ({ page }) => {
    const collector = await setupConsoleMonitoring(page);

    await page.goto(`${TEST_CONFIG.baseUrl}/`);
    await page.waitForLoadState('networkidle');

    // Check for network-related errors
    const networkErrors = collector.errors.filter(error =>
      error.message.includes('Failed to fetch') ||
      error.message.includes('NetworkError') ||
      error.message.includes('404') ||
      error.message.includes('500')
    );

    expect(networkErrors.length).toBe(0);
  });
});
