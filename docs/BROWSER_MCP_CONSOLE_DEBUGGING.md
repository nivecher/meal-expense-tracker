# Browser Console Debugging with MCP Server

## Overview

This guide provides step-by-step instructions for using the browser MCP server to identify and fix console issues in the Meal Expense Tracker application.

## Prerequisites

- Browser MCP server running
- Application running on `http://localhost:5000`
- Console debugger script (`scripts/console-debugger.js`)

## Step-by-Step Debugging Process

### 1. Navigate to the Application

```javascript
// Use MCP browser navigate tool
await mcp_playwright_browser_navigate({
  url: "http://localhost:5000"
});
```

### 2. Inject Console Debugger Script

```javascript
// Use MCP browser evaluate tool to inject the debugger
await mcp_playwright_browser_evaluate({
  expression: `
    // Load the console debugger script
    const script = document.createElement('script');
    script.src = '/static/js/console-debugger.js';
    document.head.appendChild(script);
  `
});
```

### 3. Wait for Page Load and Check Initial Console

```javascript
// Wait for page to fully load
await mcp_playwright_browser_wait_for({
  selector: "body"
});

// Check initial console state
const initialSummary = await mcp_playwright_browser_evaluate({
  expression: "window.getConsoleSummary ? window.getConsoleSummary() : 'Debugger not loaded'"
});
```

### 4. Navigate Through Key Pages

#### Home Page
```javascript
await mcp_playwright_browser_navigate({
  url: "http://localhost:5000/"
});

// Wait and check console
await mcp_playwright_browser_wait_for({
  selector: "body"
});

const homeConsole = await mcp_playwright_browser_evaluate({
  expression: "window.getConsoleSummary()"
});
```

#### Login Page
```javascript
await mcp_playwright_browser_navigate({
  url: "http://localhost:5000/auth/login"
});

await mcp_playwright_browser_wait_for({
  selector: "body"
});

const loginConsole = await mcp_playwright_browser_evaluate({
  expression: "window.getConsoleSummary()"
});
```

#### Expenses Page (After Login)
```javascript
// First login
await mcp_playwright_browser_navigate({
  url: "http://localhost:5000/auth/login"
});

await mcp_playwright_browser_fill({
  selector: "input[name='username']",
  value: "testuser_1"
});

await mcp_playwright_browser_fill({
  selector: "input[name='password']",
  value: "testpass"
});

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

const expensesConsole = await mcp_playwright_browser_evaluate({
  expression: "window.getConsoleSummary()"
});
```

### 5. Analyze Console Issues

```javascript
// Get detailed console report
const consoleReport = await mcp_playwright_browser_evaluate({
  expression: "window.generateConsoleReport()"
});

// Get critical errors
const criticalErrors = await mcp_playwright_browser_evaluate({
  expression: "window.getCriticalErrors()"
});

// Get filtered messages (issues that need attention)
const filteredMessages = await mcp_playwright_browser_evaluate({
  expression: "window.getFilteredMessages()"
});
```

### 6. Check Specific Issues

#### JavaScript Module Loading
```javascript
const moduleIssues = await mcp_playwright_browser_evaluate({
  expression: "window.consoleDebugger.checkJavaScriptModules()"
});
```

#### Console Filtering
```javascript
const consoleIssues = await mcp_playwright_browser_evaluate({
  expression: "window.consoleDebugger.checkConsoleFiltering()"
});
```

#### Performance Issues
```javascript
const performanceIssues = await mcp_playwright_browser_evaluate({
  expression: "window.consoleDebugger.checkPerformance()"
});
```

### 7. Test Interactive Elements

#### Test Form Submissions
```javascript
// Test expense form
await mcp_playwright_browser_navigate({
  url: "http://localhost:5000/expenses/add"
});

await mcp_playwright_browser_wait_for({
  selector: "body"
});

// Fill form and submit
await mcp_playwright_browser_fill({
  selector: "input[name='amount']",
  value: "25.50"
});

// Check for console errors during form interaction
const formConsole = await mcp_playwright_browser_evaluate({
  expression: "window.getConsoleSummary()"
});
```

#### Test Dynamic Content Loading
```javascript
// Test restaurant search
await mcp_playwright_browser_navigate({
  url: "http://localhost:5000/restaurants/search"
});

await mcp_playwright_browser_wait_for({
  selector: "body"
});

// Interact with search
await mcp_playwright_browser_fill({
  selector: "input[type='search']",
  value: "test"
});

// Check console during dynamic loading
const searchConsole = await mcp_playwright_browser_evaluate({
  expression: "window.getConsoleSummary()"
});
```

### 8. Export Console Data

```javascript
// Export all console data for analysis
const consoleData = await mcp_playwright_browser_evaluate({
  expression: "window.exportConsoleData()"
});

// Save to file or analyze
console.log("Console Data:", JSON.stringify(consoleData, null, 2));
```

## Common Console Issues to Look For

### 1. JavaScript Errors
- Syntax errors
- Undefined variables
- Module loading failures
- Type errors

### 2. Network Issues
- Failed resource loading
- 404 errors
- CORS issues
- Timeout errors

### 3. Performance Issues
- Slow loading times
- Memory leaks
- Long-running scripts
- Resource bottlenecks

### 4. Library Conflicts
- jQuery conflicts
- Bootstrap issues
- Font Awesome problems
- Select2 errors

## Automated Testing Script

Here's a complete script you can run with the MCP browser server:

```javascript
// Complete console debugging workflow
async function debugConsoleIssues() {
  const results = {};
  
  // 1. Home page
  await mcp_playwright_browser_navigate({ url: "http://localhost:5000/" });
  await mcp_playwright_browser_wait_for({ selector: "body" });
  results.home = await mcp_playwright_browser_evaluate({
    expression: "window.getConsoleSummary()"
  });
  
  // 2. Login page
  await mcp_playwright_browser_navigate({ url: "http://localhost:5000/auth/login" });
  await mcp_playwright_browser_wait_for({ selector: "body" });
  results.login = await mcp_playwright_browser_evaluate({
    expression: "window.getConsoleSummary()"
  });
  
  // 3. Login and go to expenses
  await mcp_playwright_browser_fill({ selector: "input[name='username']", value: "testuser_1" });
  await mcp_playwright_browser_fill({ selector: "input[name='password']", value: "testpass" });
  await mcp_playwright_browser_click({ selector: "button[type='submit']" });
  await mcp_playwright_browser_wait_for({ selector: "body" });
  
  await mcp_playwright_browser_navigate({ url: "http://localhost:5000/expenses" });
  await mcp_playwright_browser_wait_for({ selector: "body" });
  results.expenses = await mcp_playwright_browser_evaluate({
    expression: "window.getConsoleSummary()"
  });
  
  // 4. Generate final report
  const finalReport = await mcp_playwright_browser_evaluate({
    expression: "window.generateConsoleReport()"
  });
  
  return { results, finalReport };
}

// Run the debugging
const debugResults = await debugConsoleIssues();
console.log("Debug Results:", JSON.stringify(debugResults, null, 2));
```

## Fixing Common Issues

### 1. Module Loading Errors
- Check import paths
- Verify file existence
- Check for syntax errors
- Ensure proper module format

### 2. Console Filtering Issues
- Enable console filter in development
- Update filter patterns
- Check filter implementation

### 3. Performance Issues
- Optimize JavaScript loading
- Implement lazy loading
- Fix memory leaks
- Optimize DOM operations

### 4. Library Conflicts
- Update library versions
- Check for version compatibility
- Fix initialization order
- Resolve naming conflicts

## Best Practices

1. **Always check console first** when debugging issues
2. **Use the debugger script** to capture all console activity
3. **Test all major pages** and user flows
4. **Monitor performance** during interactions
5. **Export data** for detailed analysis
6. **Fix critical errors first**, then warnings
7. **Implement proper error handling** to prevent future issues

## Troubleshooting

If the debugger script doesn't load:
1. Check if the script path is correct
2. Verify the application is running
3. Check for JavaScript errors preventing script execution
4. Try injecting the script directly via MCP evaluate

If console data is empty:
1. Ensure the page has fully loaded
2. Check if there are any JavaScript errors
3. Verify the debugger script is working
4. Try refreshing the page and running again
