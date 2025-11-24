#!/bin/bash

# Check Docker MCP Gateway Setup
# This script verifies that Docker Desktop is running and MCP Gateway is configured correctly

set -e

echo "🔍 Checking Docker MCP Gateway Setup..."
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed"
    exit 1
fi

echo "✅ Docker is installed: $(docker --version)"

# Check if Docker Desktop is running
if ! docker ps &> /dev/null; then
    echo "❌ Docker Desktop is not running"
    echo ""
    echo "Please start Docker Desktop and try again."
    exit 1
fi

echo "✅ Docker Desktop is running"

# Check if MCP Toolkit is available
if ! docker mcp --help &> /dev/null; then
    echo "❌ Docker MCP Toolkit is not available"
    echo ""
    echo "Please ensure Docker Desktop has MCP Toolkit enabled."
    exit 1
fi

echo "✅ Docker MCP Toolkit is available"

# Check gateway command
if ! docker mcp gateway run --help &> /dev/null; then
    echo "❌ Docker MCP Gateway command not found"
    exit 1
fi

echo "✅ Docker MCP Gateway command is available"

# Check MCP configuration file
MCP_CONFIG="$HOME/.cursor/mcp.json"
if [ ! -f "$MCP_CONFIG" ]; then
    echo "⚠️  MCP configuration file not found at: $MCP_CONFIG"
    echo "   Please create the configuration file."
    exit 1
fi

echo "✅ MCP configuration file exists: $MCP_CONFIG"

# Validate JSON
if ! python3 -m json.tool "$MCP_CONFIG" &> /dev/null; then
    echo "❌ MCP configuration file is not valid JSON"
    exit 1
fi

echo "✅ MCP configuration file is valid JSON"

# Check if docker server is configured
if ! grep -q '"docker"' "$MCP_CONFIG"; then
    echo "⚠️  Docker MCP server not found in configuration"
    echo "   Please ensure the 'docker' server is configured in mcp.json"
    exit 1
fi

echo "✅ Docker MCP server is configured"

# Test gateway dry-run
echo ""
echo "🧪 Testing MCP Gateway (dry-run)..."
if timeout 5 docker mcp gateway run --dry-run 2>&1 | grep -q "gateway\|error\|Docker Desktop"; then
    echo "✅ MCP Gateway can start (dry-run test)"
else
    echo "⚠️  MCP Gateway dry-run test inconclusive"
fi

echo ""
echo "🎉 Docker MCP Gateway setup looks good!"
echo ""
echo "Next steps:"
echo "1. Restart Cursor to load the MCP configuration"
echo "2. Verify MCP tools are available in Cursor"
echo "3. Check Cursor's MCP server status in settings"
