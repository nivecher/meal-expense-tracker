# MCP Browser Console Debugging - Quick Reference

## Quick Start

1. **Install MCP Server**: Run `./scripts/setup-mcp.sh` or manually install:
   ```bash
   npm install -g @modelcontextprotocol/server-playwright
   ```

2. **Configure MCP**: Ensure `~/.cursor/mcp.json` is properly configured (see troubleshooting guide)

3. **Start your application**: `python app.py` (or however you run it)

4. **Restart Cursor** to load MCP configuration

5. **Open MCP browser session** and copy/paste the commands below

6. **Test MCP setup**: Run `./scripts/test-mcp.js` to verify everything works

## Essential Commands

### 1. Basic Navigation and Setup
```javascript
// Navigate to app
await mcp_playwright_browser_navigate({ url: "http://localhost:5000" });
await mcp_playwright_browser_wait_for({ selector: "body" });

// Inject console debugger
await mcp_playwright_browser_evaluate({
  expression: `
    // [Paste the console debugger script here]
  `
});
```

### 2. Check Console Status
```javascript
// Get console summary
const summary = await mcp_playwright_browser_evaluate({
  expression: "window.getConsoleSummary()"
});
console.log("Console summary:", summary);
```

### 3. Test Key Pages
```javascript
// Home page
await mcp_playwright_browser_navigate({ url: "http://localhost:5000/" });
const homeConsole = await mcp_playwright_browser_evaluate({
  expression: "window.getConsoleSummary()"
});

// Login page
await mcp_playwright_browser_navigate({ url: "http://localhost:5000/auth/login" });
const loginConsole = await mcp_playwright_browser_evaluate({
  expression: "window.getConsoleSummary()"
});

// Login and go to expenses
await mcp_playwright_browser_fill({ selector: "input[name='username']", value: "testuser_1" });
await mcp_playwright_browser_fill({ selector: "input[name='password']", value: "testpass" });
await mcp_playwright_browser_click({ selector: "button[type='submit']" });
await mcp_playwright_browser_wait_for({ selector: "body" });

await mcp_playwright_browser_navigate({ url: "http://localhost:5000/expenses" });
const expensesConsole = await mcp_playwright_browser_evaluate({
  expression: "window.getConsoleSummary()"
});
```

### 4. Check for Critical Errors
```javascript
const criticalErrors = await mcp_playwright_browser_evaluate({
  expression: "window.getCriticalErrors()"
});
console.log("Critical errors:", criticalErrors);
```

### 5. Check Expenses Display
```javascript
const expensesStatus = await mcp_playwright_browser_evaluate({
  expression: `
    {
      cardContainer: !!document.querySelector('#card-view-container'),
      tableContainer: !!document.querySelector('#table-view-container'),
      noExpenses: !!document.querySelector('.text-center.py-5'),
      expensesCount: document.querySelector('#card-view-container')?.children.length || 0
    }
  `
});
console.log("Expenses display:", expensesStatus);
```

## Complete Debugging Script

Use the complete script from `scripts/mcp-console-debug.js` for comprehensive testing.

## Common Issues and Solutions

### Issue: Expenses not displaying
**Check**: 
```javascript
const expensesStatus = await mcp_playwright_browser_evaluate({
  expression: "document.querySelector('#card-view-container')?.children.length || 0"
});
```

**Possible causes**:
- JavaScript errors preventing page load
- Database connection issues
- Authentication problems
- Template rendering errors

### Issue: Console errors
**Check**:
```javascript
const errors = await mcp_playwright_browser_evaluate({
  expression: "window.consoleDebugger.errors"
});
```

**Common fixes**:
- Fix JavaScript syntax errors
- Update module imports
- Fix undefined variables
- Resolve library conflicts

### Issue: Performance problems
**Check**:
```javascript
const performance = await mcp_playwright_browser_evaluate({
  expression: "performance.getEntriesByType('navigation')[0]"
});
```

## File Locations

- **Main script**: `scripts/mcp-console-debug.js`
- **Console debugger**: `scripts/console-debugger.js`
- **Documentation**: `docs/BROWSER_MCP_CONSOLE_DEBUGGING.md`

## Next Steps

1. Run the debugging script
2. Identify critical errors
3. Fix the issues in the code
4. Re-run the script to validate fixes
5. Repeat until console is clean
