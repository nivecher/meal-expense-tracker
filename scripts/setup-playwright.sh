#!/bin/bash

# Setup Playwright for Meal Expense Tracker
# This script installs Playwright and its dependencies

set -e

echo "🎭 Setting up Playwright for frontend testing..."

# Check if Node.js is installed
if ! command -v node >/dev/null 2>&1; then
    echo "❌ Node.js is not installed. Please install Node.js first."
    echo "   Visit: https://nodejs.org/"
    exit 1
fi

# Check if npm is installed
if ! command -v npm >/dev/null 2>&1; then
    echo "❌ npm is not installed. Please install npm first."
    exit 1
fi

echo "✅ Node.js and npm are available"

# Install npm dependencies
echo "📦 Installing npm dependencies..."
npm install

# Install Playwright browsers
echo "🌐 Installing Playwright browsers..."
npx playwright install

echo "✅ Playwright setup completed!"
echo ""
echo "🚀 You can now run frontend tests with:"
echo "   make test-frontend"
echo "   make test-security"
echo "   make test-console"
echo "   make test-e2e"
echo ""
echo "🔧 Development commands:"
echo "   make test-frontend-headed  # Run tests with visible browser"
echo "   make test-frontend-debug   # Run tests in debug mode"
echo "   make test-report           # Generate HTML test report"
