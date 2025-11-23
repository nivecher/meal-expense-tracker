/**
 * MCP Browser Console Debugging Script
 *
 * This script provides ready-to-use MCP browser commands
 * for debugging console issues in the Meal Expense Tracker.
 *
 * Copy and paste these commands into your MCP browser session.
 */

// ============================================================================
// STEP 1: Navigate to the application and inject debugger
// ============================================================================

// Check if MCP browser tools are available
if (typeof mcp_playwright_browser_navigate === 'undefined') {
  console.error("❌ MCP Playwright browser tools not available. Please ensure MCP server is running.");
  console.error("   Run: npm install -g @modelcontextprotocol/server-playwright");
  console.error("   Then restart Cursor to load the MCP configuration.");
  process.exit(1);
}

console.log("🔧 Starting MCP Console Debugging...");

// Navigate to home page
console.log("📍 Navigating to home page...");
await mcp_playwright_browser_navigate({
  url: "http://localhost:5000"
});

// Wait for page load
console.log("⏳ Waiting for page to load...");
await mcp_playwright_browser_wait_for({
  selector: "body"
});

// Inject console debugger script
await mcp_playwright_browser_evaluate({
  expression: `
    (function() {
      'use strict';

      class ConsoleDebugger {
        constructor() {
          this.messages = [];
          this.errors = [];
          this.warnings = [];
          this.logs = [];
          this.startMonitoring();
        }

        startMonitoring() {
          const originalConsole = {
            log: console.log,
            warn: console.warn,
            error: console.error,
            info: console.info,
            debug: console.debug,
          };

          console.log = (...args) => {
            this.captureMessage('log', args);
            originalConsole.log.apply(console, args);
          };

          console.warn = (...args) => {
            this.captureMessage('warn', args);
            originalConsole.warn.apply(console, args);
          };

          console.error = (...args) => {
            this.captureMessage('error', args);
            originalConsole.error.apply(console, args);
          };

          console.info = (...args) => {
            this.captureMessage('info', args);
            originalConsole.info.apply(console, args);
          };

          console.debug = (...args) => {
            this.captureMessage('debug', args);
            originalConsole.debug.apply(console, args);
          };

          window.addEventListener('error', (event) => {
            this.captureError('JavaScript Error', event.error, event.filename, event.lineno);
          });

          window.addEventListener('unhandledrejection', (event) => {
            this.captureError('Unhandled Promise Rejection', event.reason);
          });
        }

        captureMessage(type, args) {
          const message = {
            type,
            message: args.map(arg => typeof arg === 'string' ? arg : JSON.stringify(arg)).join(' '),
            timestamp: new Date().toISOString(),
          };

          this.messages.push(message);

          switch (type) {
            case 'error':
              this.errors.push(message);
              break;
            case 'warn':
              this.warnings.push(message);
              break;
            case 'log':
              this.logs.push(message);
              break;
          }
        }

        captureError(type, error, filename, lineno) {
          const errorMessage = {
            type: 'error',
            message: \`\${type}: \${error?.message || error}\`,
            filename: filename || 'unknown',
            lineno: lineno || 0,
            timestamp: new Date().toISOString(),
          };

          this.messages.push(errorMessage);
          this.errors.push(errorMessage);
        }

        getCriticalErrors() {
          const filteredPatterns = [
            /Bootstrap.*deprecated/i,
            /jQuery.*deprecated/i,
            /Font Awesome.*deprecated/i,
            /Select2.*deprecated/i,
            /Chart\\.js.*deprecated/i,
            /cdn\\.jsdelivr\\.net/i,
            /cdnjs\\.cloudflare\\.com/i,
            /chrome-extension/i,
            /moz-extension/i,
            /webkit.*not supported/i,
          ];

          return this.errors.filter(error =>
            !filteredPatterns.some(pattern => pattern.test(error.message))
          );
        }

        getSummary() {
          const critical = this.getCriticalErrors();
          return {
            total: this.messages.length,
            errors: this.errors.length,
            warnings: this.warnings.length,
            logs: this.logs.length,
            critical: critical.length,
          };
        }
      }

      window.consoleDebugger = new ConsoleDebugger();
      window.getConsoleSummary = () => window.consoleDebugger.getSummary();
      window.getCriticalErrors = () => window.consoleDebugger.getCriticalErrors();

      console.log('🔧 Console Debugger active');
    })();
  `
});

// ============================================================================
// STEP 2: Check initial console state
// ============================================================================

// Get console summary
const homeConsole = await mcp_playwright_browser_evaluate({
  expression: "window.getConsoleSummary()"
});

console.log("Home page console summary:", homeConsole);

// ============================================================================
// STEP 3: Navigate to login page
// ============================================================================

await mcp_playwright_browser_navigate({
  url: "http://localhost:5000/auth/login"
});

await mcp_playwright_browser_wait_for({
  selector: "body"
});

const loginConsole = await mcp_playwright_browser_evaluate({
  expression: "window.getConsoleSummary()"
});

console.log("Login page console summary:", loginConsole);

// ============================================================================
// STEP 4: Login and navigate to expenses
// ============================================================================

// Fill login form
await mcp_playwright_browser_fill({
  selector: "input[name='username']",
  value: "testuser_1"
});

await mcp_playwright_browser_fill({
  selector: "input[name='password']",
  value: "testpass"
});

// Submit login
await mcp_playwright_browser_click({
  selector: "button[type='submit']"
});

// Wait for redirect
await mcp_playwright_browser_wait_for({
  selector: "body"
});

// Navigate to expenses
await mcp_playwright_browser_navigate({
  url: "http://localhost:5000/expenses"
});

await mcp_playwright_browser_wait_for({
  selector: "body"
});

// Wait a bit for any async operations
await mcp_playwright_browser_evaluate({
  expression: "new Promise(resolve => setTimeout(resolve, 2000))"
});

const expensesConsole = await mcp_playwright_browser_evaluate({
  expression: "window.getConsoleSummary()"
});

console.log("Expenses page console summary:", expensesConsole);

// ============================================================================
// STEP 5: Check for critical errors
// ============================================================================

const criticalErrors = await mcp_playwright_browser_evaluate({
  expression: "window.getCriticalErrors()"
});

console.log("Critical errors:", criticalErrors);

// ============================================================================
// STEP 6: Test other pages
// ============================================================================

// Test restaurants page
await mcp_playwright_browser_navigate({
  url: "http://localhost:5000/restaurants"
});

await mcp_playwright_browser_wait_for({
  selector: "body"
});

const restaurantsConsole = await mcp_playwright_browser_evaluate({
  expression: "window.getConsoleSummary()"
});

console.log("Restaurants page console summary:", restaurantsConsole);

// Test add expense page
await mcp_playwright_browser_navigate({
  url: "http://localhost:5000/expenses/add"
});

await mcp_playwright_browser_wait_for({
  selector: "body"
});

const addExpenseConsole = await mcp_playwright_browser_evaluate({
  expression: "window.getConsoleSummary()"
});

console.log("Add expense page console summary:", addExpenseConsole);

// ============================================================================
// STEP 7: Generate final report
// ============================================================================

const finalReport = await mcp_playwright_browser_evaluate({
  expression: `
    {
      home: window.consoleDebugger.getSummary(),
      criticalErrors: window.consoleDebugger.getCriticalErrors(),
      allMessages: window.consoleDebugger.messages,
      url: window.location.href,
      timestamp: new Date().toISOString()
    }
  `
});

console.log("Final console report:", JSON.stringify(finalReport, null, 2));

// ============================================================================
// STEP 8: Check specific issues
// ============================================================================

// Check if expenses are loading
const expensesVisible = await mcp_playwright_browser_evaluate({
  expression: `
    const cardContainer = document.querySelector('#card-view-container');
    const tableContainer = document.querySelector('#table-view-container');
    const noExpenses = document.querySelector('.text-center.py-5');

    return {
      cardContainer: !!cardContainer,
      tableContainer: !!tableContainer,
      noExpenses: !!noExpenses,
      cardContainerVisible: cardContainer ? !cardContainer.classList.contains('d-none') : false,
      tableContainerVisible: tableContainer ? !tableContainer.classList.contains('d-none') : false,
      expensesCount: cardContainer ? cardContainer.children.length : 0
    };
  `
});

console.log("Expenses display status:", expensesVisible);

// Check for JavaScript errors that might prevent expenses from loading
const jsErrors = await mcp_playwright_browser_evaluate({
  expression: `
    window.consoleDebugger.errors.filter(error =>
      error.message.includes('expense') ||
      error.message.includes('Expense') ||
      error.message.includes('module') ||
      error.message.includes('import') ||
      error.message.includes('Failed to load')
    );
  `
});

console.log("JavaScript errors related to expenses:", jsErrors);

// ============================================================================
// SUMMARY
// ============================================================================

console.log("\n=== CONSOLE DEBUGGING SUMMARY ===");
console.log("Home page issues:", homeConsole.critical);
console.log("Login page issues:", loginConsole.critical);
console.log("Expenses page issues:", expensesConsole.critical);
console.log("Restaurants page issues:", restaurantsConsole.critical);
console.log("Add expense page issues:", addExpenseConsole.critical);
console.log("Total critical errors:", criticalErrors.length);
console.log("Expenses display working:", expensesVisible.cardContainer || expensesVisible.tableContainer);
console.log("Expenses count:", expensesVisible.expensesCount);

if (criticalErrors.length > 0) {
  console.log("\n=== CRITICAL ERRORS TO FIX ===");
  criticalErrors.forEach((error, index) => {
    console.log(`${index + 1}. ${error.message}`);
    if (error.filename) {
      console.log(`   File: ${error.filename}:${error.lineno}`);
    }
  });
}
