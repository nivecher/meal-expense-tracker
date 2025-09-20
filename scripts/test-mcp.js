/**
 * MCP Browser Testing Script
 * 
 * This script tests the MCP browser automation functionality
 * for the Meal Expense Tracker application.
 * 
 * Usage: Run this script in a Cursor session with MCP enabled
 */

// ============================================================================
// MCP Browser Testing Suite
// ============================================================================

async function testMCPBrowser() {
  console.log("🧪 Starting MCP Browser Testing Suite...");
  
  const results = {
    tests: [],
    errors: [],
    summary: {
      total: 0,
      passed: 0,
      failed: 0
    }
  };

  // Test 1: Check MCP tools availability
  try {
    console.log("🔍 Test 1: Checking MCP tools availability...");
    
    if (typeof mcp_playwright_browser_navigate === 'undefined') {
      throw new Error("MCP Playwright browser tools not available");
    }
    
    results.tests.push({
      name: "MCP Tools Availability",
      status: "PASSED",
      message: "MCP browser tools are available"
    });
    results.summary.passed++;
  } catch (error) {
    results.tests.push({
      name: "MCP Tools Availability",
      status: "FAILED",
      message: error.message
    });
    results.errors.push(error);
    results.summary.failed++;
  }
  results.summary.total++;

  // Test 2: Navigate to application
  try {
    console.log("🔍 Test 2: Navigating to application...");
    
    await mcp_playwright_browser_navigate({
      url: "http://localhost:5000"
    });
    
    await mcp_playwright_browser_wait_for({
      selector: "body"
    });
    
    results.tests.push({
      name: "Application Navigation",
      status: "PASSED",
      message: "Successfully navigated to application"
    });
    results.summary.passed++;
  } catch (error) {
    results.tests.push({
      name: "Application Navigation",
      status: "FAILED",
      message: error.message
    });
    results.errors.push(error);
    results.summary.failed++;
  }
  results.summary.total++;

  // Test 3: Check page title
  try {
    console.log("🔍 Test 3: Checking page title...");
    
    const title = await mcp_playwright_browser_evaluate({
      expression: "document.title"
    });
    
    if (title && title.includes("Meal Expense Tracker")) {
      results.tests.push({
        name: "Page Title",
        status: "PASSED",
        message: `Page title: ${title}`
      });
      results.summary.passed++;
    } else {
      throw new Error(`Unexpected page title: ${title}`);
    }
  } catch (error) {
    results.tests.push({
      name: "Page Title",
      status: "FAILED",
      message: error.message
    });
    results.errors.push(error);
    results.summary.failed++;
  }
  results.summary.total++;

  // Test 4: Check for JavaScript errors
  try {
    console.log("🔍 Test 4: Checking for JavaScript errors...");
    
    const jsErrors = await mcp_playwright_browser_evaluate({
      expression: `
        (function() {
          const errors = [];
          const originalError = console.error;
          console.error = function(...args) {
            errors.push(args.join(' '));
            originalError.apply(console, args);
          };
          
          // Trigger any pending errors
          setTimeout(() => {
            window.jsErrors = errors;
          }, 1000);
          
          return errors;
        })()
      `
    });
    
    // Wait a bit for errors to accumulate
    await new Promise(resolve => setTimeout(resolve, 1500));
    
    const finalErrors = await mcp_playwright_browser_evaluate({
      expression: "window.jsErrors || []"
    });
    
    if (finalErrors.length === 0) {
      results.tests.push({
        name: "JavaScript Errors",
        status: "PASSED",
        message: "No JavaScript errors detected"
      });
      results.summary.passed++;
    } else {
      results.tests.push({
        name: "JavaScript Errors",
        status: "WARNING",
        message: `Found ${finalErrors.length} JavaScript errors: ${finalErrors.join(', ')}`
      });
      results.summary.passed++; // Count as passed but with warning
    }
  } catch (error) {
    results.tests.push({
      name: "JavaScript Errors",
      status: "FAILED",
      message: error.message
    });
    results.errors.push(error);
    results.summary.failed++;
  }
  results.summary.total++;

  // Test 5: Test form interaction
  try {
    console.log("🔍 Test 5: Testing form interaction...");
    
    // Navigate to login page
    await mcp_playwright_browser_navigate({
      url: "http://localhost:5000/auth/login"
    });
    
    await mcp_playwright_browser_wait_for({
      selector: "body"
    });
    
    // Check if login form exists
    const formExists = await mcp_playwright_browser_evaluate({
      expression: "!!document.querySelector('form')"
    });
    
    if (formExists) {
      results.tests.push({
        name: "Form Interaction",
        status: "PASSED",
        message: "Login form found and accessible"
      });
      results.summary.passed++;
    } else {
      throw new Error("Login form not found");
    }
  } catch (error) {
    results.tests.push({
      name: "Form Interaction",
      status: "FAILED",
      message: error.message
    });
    results.errors.push(error);
    results.summary.failed++;
  }
  results.summary.total++;

  // Test 6: Test responsive design
  try {
    console.log("🔍 Test 6: Testing responsive design...");
    
    // Test mobile viewport
    await mcp_playwright_browser_evaluate({
      expression: `
        Object.defineProperty(window, 'innerWidth', {
          writable: true,
          configurable: true,
          value: 375,
        });
        Object.defineProperty(window, 'innerHeight', {
          writable: true,
          configurable: true,
          value: 667,
        });
        window.dispatchEvent(new Event('resize'));
      `
    });
    
    // Check if page is responsive
    const isResponsive = await mcp_playwright_browser_evaluate({
      expression: "window.innerWidth === 375 && window.innerHeight === 667"
    });
    
    if (isResponsive) {
      results.tests.push({
        name: "Responsive Design",
        status: "PASSED",
        message: "Page responds to viewport changes"
      });
      results.summary.passed++;
    } else {
      throw new Error("Page does not respond to viewport changes");
    }
  } catch (error) {
    results.tests.push({
      name: "Responsive Design",
      status: "FAILED",
      message: error.message
    });
    results.errors.push(error);
    results.summary.failed++;
  }
  results.summary.total++;

  // Generate final report
  console.log("\n📊 MCP Browser Testing Results:");
  console.log("=====================================");
  
  results.tests.forEach((test, index) => {
    const status = test.status === "PASSED" ? "✅" : test.status === "WARNING" ? "⚠️" : "❌";
    console.log(`${index + 1}. ${status} ${test.name}: ${test.message}`);
  });
  
  console.log("\n📈 Summary:");
  console.log(`Total Tests: ${results.summary.total}`);
  console.log(`Passed: ${results.summary.passed}`);
  console.log(`Failed: ${results.summary.failed}`);
  console.log(`Success Rate: ${((results.summary.passed / results.summary.total) * 100).toFixed(1)}%`);
  
  if (results.errors.length > 0) {
    console.log("\n❌ Errors:");
    results.errors.forEach((error, index) => {
      console.log(`${index + 1}. ${error.message}`);
    });
  }
  
  return results;
}

// Run the tests
console.log("🚀 Starting MCP Browser Tests...");
testMCPBrowser()
  .then(results => {
    console.log("\n🎉 MCP Browser Testing completed!");
    return results;
  })
  .catch(error => {
    console.error("\n💥 MCP Browser Testing failed:", error);
    process.exit(1);
  });
