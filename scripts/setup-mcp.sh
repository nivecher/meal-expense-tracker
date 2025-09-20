#!/bin/bash

# MCP Server Setup Script for Meal Expense Tracker
# This script sets up the MCP (Model Context Protocol) server for browser automation

set -e

echo "🔧 Setting up MCP Server for Meal Expense Tracker..."

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is not installed. Please install Node.js first."
    echo "   Visit: https://nodejs.org/"
    exit 1
fi

# Check if npm is installed
if ! command -v npm &> /dev/null; then
    echo "❌ npm is not installed. Please install npm first."
    exit 1
fi

echo "✅ Node.js and npm are available"

# Install MCP Playwright server globally
echo "📦 Installing MCP Playwright server..."
npm install -g @playwright/mcp

# Verify installation
if npx @playwright/mcp --help &> /dev/null; then
    echo "✅ MCP Playwright server installed successfully"
else
    echo "❌ Failed to install MCP Playwright server"
    exit 1
fi

# Create MCP configuration directory if it doesn't exist
MCP_CONFIG_DIR="$HOME/.cursor"
if [ ! -d "$MCP_CONFIG_DIR" ]; then
    mkdir -p "$MCP_CONFIG_DIR"
    echo "✅ Created MCP configuration directory: $MCP_CONFIG_DIR"
fi

# Check if MCP configuration exists
if [ -f "$MCP_CONFIG_DIR/mcp.json" ]; then
    echo "✅ MCP configuration found at: $MCP_CONFIG_DIR/mcp.json"
else
    echo "⚠️  MCP configuration not found. Please ensure mcp.json is properly configured."
fi

# Test MCP server connection
echo "🧪 Testing MCP server connection..."
if npx @playwright/mcp --help &> /dev/null; then
    echo "✅ MCP Playwright server is working correctly"
else
    echo "❌ MCP Playwright server test failed"
    exit 1
fi

echo ""
echo "🎉 MCP Server setup completed successfully!"
echo ""
echo "Next steps:"
echo "1. Restart Cursor to load the MCP configuration"
echo "2. Use the MCP browser tools to test the application"
echo "3. Run the debugging scripts in scripts/mcp-console-debug.js"
echo ""
echo "Available MCP tools:"
echo "- mcp_playwright_browser_navigate"
echo "- mcp_playwright_browser_evaluate"
echo "- mcp_playwright_browser_click"
echo "- mcp_playwright_browser_fill"
echo "- mcp_playwright_browser_wait_for"
echo ""
echo "For more information, see:"
echo "- docs/BROWSER_MCP_CONSOLE_DEBUGGING.md"
echo "- docs/MCP_BROWSER_QUICK_REFERENCE.md"
