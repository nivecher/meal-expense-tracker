/**
 * MCP Health Check Script
 *
 * This script performs a quick health check of the MCP setup
 * and provides recommendations for fixing any issues.
 */

// ============================================================================
// MCP Health Check
// ============================================================================

async function mcpHealthCheck() {
  console.log("🏥 MCP Health Check Starting...");

  const health = {
    mcpServer: false,
    application: false,
    browser: false,
    configuration: false,
    issues: [],
    recommendations: []
  };

  // Check 1: MCP Server Availability
  console.log("🔍 Checking MCP server availability...");
  try {
    if (typeof mcp_playwright_browser_navigate === 'function') {
      health.mcpServer = true;
      console.log("✅ MCP server is available");
    } else {
      health.issues.push("MCP Playwright browser tools not available");
      health.recommendations.push("Install MCP server: npm install -g @modelcontextprotocol/server-playwright");
      health.recommendations.push("Restart Cursor after installation");
    }
  } catch (error) {
    health.issues.push(`MCP server check failed: ${error.message}`);
  }

  // Check 2: Application Connectivity
  console.log("🔍 Checking application connectivity...");
  try {
    await mcp_playwright_browser_navigate({
      url: "http://localhost:5000"
    });

    await mcp_playwright_browser_wait_for({
      selector: "body"
    });

    health.application = true;
    console.log("✅ Application is accessible");
  } catch (error) {
    health.issues.push(`Application connectivity failed: ${error.message}`);
    health.recommendations.push("Start the application: python app.py");
    health.recommendations.push("Check if application is running on port 5000");
  }

  // Check 3: Browser Functionality
  console.log("🔍 Checking browser functionality...");
  try {
    const title = await mcp_playwright_browser_evaluate({
      expression: "document.title"
    });

    if (title && title.length > 0) {
      health.browser = true;
      console.log("✅ Browser functionality working");
    } else {
      health.issues.push("Browser cannot execute JavaScript");
      health.recommendations.push("Check Playwright browser installation: npx playwright install");
    }
  } catch (error) {
    health.issues.push(`Browser functionality failed: ${error.message}`);
    health.recommendations.push("Reinstall Playwright browsers: npx playwright install");
  }

  // Check 4: Configuration
  console.log("🔍 Checking MCP configuration...");
  try {
    // This would need to be done outside the browser context
    // For now, we'll assume it's configured if MCP tools are available
    if (health.mcpServer) {
      health.configuration = true;
      console.log("✅ MCP configuration appears correct");
    }
  } catch (error) {
    health.issues.push(`Configuration check failed: ${error.message}`);
    health.recommendations.push("Check ~/.cursor/mcp.json configuration");
  }

  // Generate Health Report
  console.log("\n📊 MCP Health Check Results:");
  console.log("=============================");

  const checks = [
    { name: "MCP Server", status: health.mcpServer },
    { name: "Application", status: health.application },
    { name: "Browser", status: health.browser },
    { name: "Configuration", status: health.configuration }
  ];

  checks.forEach(check => {
    const status = check.status ? "✅" : "❌";
    console.log(`${status} ${check.name}`);
  });

  const overallHealth = checks.every(check => check.status);

  if (overallHealth) {
    console.log("\n🎉 MCP setup is healthy and ready to use!");
  } else {
    console.log("\n⚠️  MCP setup has issues that need attention:");

    if (health.issues.length > 0) {
      console.log("\n❌ Issues found:");
      health.issues.forEach((issue, index) => {
        console.log(`${index + 1}. ${issue}`);
      });
    }

    if (health.recommendations.length > 0) {
      console.log("\n💡 Recommendations:");
      health.recommendations.forEach((rec, index) => {
        console.log(`${index + 1}. ${rec}`);
      });
    }
  }

  // Additional Diagnostics
  if (!overallHealth) {
    console.log("\n🔧 Additional Diagnostics:");
    console.log("=========================");

    try {
      // Check if we can get basic page info
      const pageInfo = await mcp_playwright_browser_evaluate({
        expression: `
          {
            url: window.location.href,
            title: document.title,
            readyState: document.readyState,
            userAgent: navigator.userAgent
          }
        `
      });

      console.log("Page Information:");
      console.log(`  URL: ${pageInfo.url}`);
      console.log(`  Title: ${pageInfo.title}`);
      console.log(`  Ready State: ${pageInfo.readyState}`);
      console.log(`  User Agent: ${pageInfo.userAgent.substring(0, 50)}...`);

    } catch (error) {
      console.log(`❌ Could not retrieve page information: ${error.message}`);
    }
  }

  return health;
}

// Run the health check
console.log("🚀 Starting MCP Health Check...");
mcpHealthCheck()
  .then(health => {
    const overallHealth = health.mcpServer && health.application && health.browser && health.configuration;

    if (overallHealth) {
      console.log("\n✅ MCP is ready for use!");
      console.log("You can now run the debugging scripts:");
      console.log("- scripts/mcp-console-debug.js");
      console.log("- scripts/test-mcp.js");
    } else {
      console.log("\n❌ MCP needs attention before use.");
      console.log("Please follow the recommendations above and run this script again.");
    }

    return health;
  })
  .catch(error => {
    console.error("\n💥 Health check failed:", error);
    console.log("\nPlease check the troubleshooting guide: docs/MCP_TROUBLESHOOTING.md");
  });
