# MCP Troubleshooting Guide

## Overview

This guide helps you troubleshoot common issues with the Model Context Protocol (MCP) browser automation setup for the Meal Expense Tracker.

## Common Issues and Solutions

### 1. MCP Tools Not Available

**Error**: `mcp_playwright_browser_navigate is not defined`

**Causes**:

- MCP server not installed
- MCP configuration incorrect
- Cursor not restarted after configuration changes

**Solutions**:

1. **Install MCP Playwright Server**:

   ```bash
   npm install -g @modelcontextprotocol/server-playwright
   ```

2. **Verify Installation**:

   ```bash
   npx @modelcontextprotocol/server-playwright --help
   ```

3. **Check MCP Configuration**:

   ```bash
   cat ~/.cursor/mcp.json
   ```

   Should contain:

   ```json
   {
     "mcpServers": {
       "playwright": {
         "command": "npx",
         "args": ["@modelcontextprotocol/server-playwright"],
         "env": {
           "NODE_ENV": "development"
         },
         "enabled": true
       }
     }
   }
   ```

4. **Restart Cursor** after configuration changes

### 2. Application Not Running

**Error**: `Navigation failed` or `Connection refused`

**Causes**:

- Application not started
- Wrong port number
- Firewall blocking connection

**Solutions**:

1. **Start the Application**:

   ```bash
   cd /home/mtd37/workspace/meal-expense-tracker
   source venv/bin/activate
   python app.py
   ```

2. **Check if Application is Running**:

   ```bash
   curl http://localhost:5000
   ```

3. **Verify Port Configuration**:
   - Check `config.py` for port settings
   - Ensure no other service is using port 5000

### 3. Browser Automation Fails

**Error**: `Browser launch failed` or `Page not found`

**Causes**:

- Playwright browser not installed
- Insufficient permissions
- Network issues

**Solutions**:

1. **Install Playwright Browsers**:

   ```bash
   npx playwright install
   ```

2. **Check Permissions**:

   ```bash
   ls -la ~/.cache/ms-playwright/
   ```

3. **Test Browser Manually**:
   ```bash
   npx playwright test --headed
   ```

### 4. Console Debugging Script Issues

**Error**: `Console debugger not loaded` or `getConsoleSummary is not a function`

**Causes**:

- Script injection failed
- JavaScript errors preventing execution
- Page not fully loaded

**Solutions**:

1. **Check Script Injection**:

   ```javascript
   await mcp_playwright_browser_evaluate({
     expression: "typeof window.consoleDebugger",
   });
   ```

2. **Verify Page Load**:

   ```javascript
   await mcp_playwright_browser_wait_for({
     selector: "body",
   });
   ```

3. **Check for JavaScript Errors**:
   ```javascript
   await mcp_playwright_browser_evaluate({
     expression: "window.consoleDebugger.errors",
   });
   ```

### 5. Performance Issues

**Symptoms**:

- Slow page loads
- Timeout errors
- Memory issues

**Solutions**:

1. **Optimize Browser Settings**:

   ```javascript
   await mcp_playwright_browser_navigate({
     url: "http://localhost:5000",
     options: {
       waitUntil: "networkidle",
       timeout: 30000,
     },
   });
   ```

2. **Check System Resources**:

   ```bash
   free -h
   top -p $(pgrep -f "playwright")
   ```

3. **Reduce Concurrent Operations**:
   - Run tests sequentially
   - Add delays between operations
   - Close unused browser contexts

## Diagnostic Commands

### Check MCP Server Status

```bash
# Check if MCP server is running
ps aux | grep playwright

# Check MCP configuration
cat ~/.cursor/mcp.json

# Test MCP server
npx @modelcontextprotocol/server-playwright --help
```

### Check Application Status

```bash
# Check if application is running
ps aux | grep python | grep app.py

# Test application endpoint
curl -I http://localhost:5000

# Check application logs
tail -f /var/log/meal-expense-tracker.log
```

### Check Browser Status

```bash
# Check Playwright installation
npx playwright --version

# Check browser installation
npx playwright install --dry-run

# Test browser launch
npx playwright test --headed --browser=chromium
```

## Debugging Steps

### 1. Basic Connectivity Test

```javascript
// Test basic MCP functionality
try {
  await mcp_playwright_browser_navigate({
    url: "http://localhost:5000",
  });
  console.log("✅ Basic navigation works");
} catch (error) {
  console.error("❌ Navigation failed:", error);
}
```

### 2. Page Load Test

```javascript
// Test page loading
try {
  await mcp_playwright_browser_wait_for({
    selector: "body",
  });
  console.log("✅ Page loaded successfully");
} catch (error) {
  console.error("❌ Page load failed:", error);
}
```

### 3. JavaScript Execution Test

```javascript
// Test JavaScript execution
try {
  const result = await mcp_playwright_browser_evaluate({
    expression: "document.title",
  });
  console.log("✅ JavaScript execution works:", result);
} catch (error) {
  console.error("❌ JavaScript execution failed:", error);
}
```

### 4. Console Debugging Test

```javascript
// Test console debugging
try {
  await mcp_playwright_browser_evaluate({
    expression: `
      if (typeof window.consoleDebugger === 'undefined') {
        throw new Error('Console debugger not loaded');
      }
      window.consoleDebugger.getSummary();
    `,
  });
  console.log("✅ Console debugging works");
} catch (error) {
  console.error("❌ Console debugging failed:", error);
}
```

## Advanced Troubleshooting

### 1. Network Issues

```bash
# Check network connectivity
ping localhost
telnet localhost 5000

# Check firewall rules
sudo ufw status
sudo iptables -L
```

### 2. Permission Issues

```bash
# Check file permissions
ls -la ~/.cursor/
ls -la ~/.cache/ms-playwright/

# Fix permissions if needed
chmod 755 ~/.cursor/
chmod -R 755 ~/.cache/ms-playwright/
```

### 3. Resource Issues

```bash
# Check memory usage
free -h
ps aux --sort=-%mem | head -10

# Check disk space
df -h
du -sh ~/.cache/ms-playwright/
```

### 4. Configuration Issues

```bash
# Validate JSON configuration
python -m json.tool ~/.cursor/mcp.json

# Check Node.js version
node --version
npm --version

# Check Playwright version
npx playwright --version
```

## Getting Help

### 1. Check Logs

```bash
# Application logs
tail -f /var/log/meal-expense-tracker.log

# System logs
journalctl -u meal-expense-tracker

# Browser logs
ls -la ~/.cache/ms-playwright/
```

### 2. Enable Debug Mode

```bash
# Enable MCP debug mode
export DEBUG=mcp:*
npx @modelcontextprotocol/server-playwright

# Enable Playwright debug mode
export DEBUG=pw:*
npx playwright test --headed
```

### 3. Create Support Package

```bash
# Create diagnostic package
mkdir -p /tmp/mcp-debug
cp ~/.cursor/mcp.json /tmp/mcp-debug/
ps aux > /tmp/mcp-debug/processes.txt
free -h > /tmp/mcp-debug/memory.txt
df -h > /tmp/mcp-debug/disk.txt
tar -czf /tmp/mcp-debug.tar.gz /tmp/mcp-debug/
```

## Prevention

### 1. Regular Maintenance

- Update MCP server regularly
- Clean browser cache periodically
- Monitor system resources
- Keep application updated

### 2. Best Practices

- Always restart Cursor after configuration changes
- Test MCP functionality before running complex scripts
- Use proper error handling in scripts
- Keep debugging scripts up to date

### 3. Monitoring

- Set up application monitoring
- Monitor system resources
- Track MCP server performance
- Log all automation activities

## Quick Fixes

### Reset MCP Configuration

```bash
# Backup current configuration
cp ~/.cursor/mcp.json ~/.cursor/mcp.json.backup

# Reset to default
cat > ~/.cursor/mcp.json << EOF
{
  "mcpServers": {
    "playwright": {
      "command": "npx",
      "args": ["@modelcontextprotocol/server-playwright"],
      "env": {
        "NODE_ENV": "development"
      },
      "enabled": true
    }
  }
}
EOF
```

### Reinstall MCP Server

```bash
# Uninstall
npm uninstall -g @modelcontextprotocol/server-playwright

# Reinstall
npm install -g @modelcontextprotocol/server-playwright

# Restart Cursor
```

### Clear Browser Cache

```bash
# Clear Playwright cache
rm -rf ~/.cache/ms-playwright/

# Reinstall browsers
npx playwright install
```

## Contact Support

If you continue to experience issues:

1. **Check this guide** for your specific error
2. **Run diagnostic commands** to gather information
3. **Create support package** with system information
4. **Contact the development team** with detailed error information

Include in your support request:

- Error messages
- System information
- Steps to reproduce
- Diagnostic output
- Support package (if applicable)
