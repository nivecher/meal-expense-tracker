/**
 * Browser Console Debugger Script
 * 
 * This script can be injected into the browser using the MCP server
 * to identify and fix console issues in the Meal Expense Tracker.
 * 
 * Usage with MCP Browser Server:
 * 1. Navigate to the application
 * 2. Inject this script using evaluateJavaScript
 * 3. Run the debugging functions
 * 4. Analyze the results
 * 
 * @version 1.0.0
 * @author Meal Expense Tracker Team
 */

(function() {
  'use strict';

  // Console message collector
  class ConsoleDebugger {
    constructor() {
      this.messages = [];
      this.errors = [];
      this.warnings = [];
      this.logs = [];
      this.performanceIssues = [];
      this.moduleErrors = [];
      
      this.originalConsole = {
        log: console.log,
        warn: console.warn,
        error: console.error,
        info: console.info,
        debug: console.debug,
      };
      
      this.startMonitoring();
    }

    startMonitoring() {
      // Override console methods to capture messages
      console.log = (...args) => {
        this.captureMessage('log', args);
        this.originalConsole.log.apply(console, args);
      };

      console.warn = (...args) => {
        this.captureMessage('warn', args);
        this.originalConsole.warn.apply(console, args);
      };

      console.error = (...args) => {
        this.captureMessage('error', args);
        this.originalConsole.error.apply(console, args);
      };

      console.info = (...args) => {
        this.captureMessage('info', args);
        this.originalConsole.info.apply(console, args);
      };

      console.debug = (...args) => {
        this.captureMessage('debug', args);
        this.originalConsole.debug.apply(console, args);
      };

      // Monitor unhandled errors
      window.addEventListener('error', (event) => {
        this.captureError('JavaScript Error', event.error, event.filename, event.lineno);
      });

      // Monitor unhandled promise rejections
      window.addEventListener('unhandledrejection', (event) => {
        this.captureError('Unhandled Promise Rejection', event.reason);
      });

      // Monitor resource loading errors
      window.addEventListener('error', (event) => {
        if (event.target !== window) {
          this.captureError('Resource Loading Error', `Failed to load: ${event.target.src || event.target.href}`);
        }
      }, true);
    }

    captureMessage(type, args) {
      const message = {
        type,
        message: args.map(arg => typeof arg === 'string' ? arg : JSON.stringify(arg)).join(' '),
        timestamp: new Date().toISOString(),
        stack: new Error().stack,
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
        message: `${type}: ${error?.message || error}`,
        filename: filename || 'unknown',
        lineno: lineno || 0,
        timestamp: new Date().toISOString(),
        stack: error?.stack || new Error().stack,
      };

      this.messages.push(errorMessage);
      this.errors.push(errorMessage);
    }

    // Analysis methods
    getCriticalErrors() {
      const filteredPatterns = [
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

      return this.errors.filter(error => 
        !filteredPatterns.some(pattern => pattern.test(error.message))
      );
    }

    getFilteredMessages() {
      const filteredPatterns = [
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

      return this.messages.filter(msg => 
        !filteredPatterns.some(pattern => pattern.test(msg.message))
      );
    }

    getModuleErrors() {
      return this.errors.filter(error => 
        error.message.includes('Failed to load') ||
        error.message.includes('Module not found') ||
        error.message.includes('import') ||
        error.message.includes('require') ||
        error.message.includes('Cannot resolve')
      );
    }

    getPerformanceIssues() {
      return this.warnings.filter(warning => 
        warning.message.includes('performance') ||
        warning.message.includes('slow') ||
        warning.message.includes('timeout') ||
        warning.message.includes('memory')
      );
    }

    getSummary() {
      const critical = this.getCriticalErrors();
      const filtered = this.getFilteredMessages();
      const moduleErrors = this.getModuleErrors();
      const performanceIssues = this.getPerformanceIssues();

      return {
        total: this.messages.length,
        errors: this.errors.length,
        warnings: this.warnings.length,
        logs: this.logs.length,
        critical: critical.length,
        filtered: filtered.length,
        moduleErrors: moduleErrors.length,
        performanceIssues: performanceIssues.length,
      };
    }

    // Diagnostic methods
    checkJavaScriptModules() {
      const issues = [];
      
      // Check if main modules are loaded
      const mainScript = document.querySelector('script[src*="main.js"]');
      if (!mainScript) {
        issues.push('Main JavaScript file not found');
      }

      // Check for module loading errors
      const moduleErrors = this.getModuleErrors();
      if (moduleErrors.length > 0) {
        issues.push(`Module loading errors: ${moduleErrors.length}`);
      }

      // Check if error handler is available
      if (typeof window.getErrorStats !== 'function') {
        issues.push('Error handler not available');
      }

      return issues;
    }

    checkConsoleFiltering() {
      const issues = [];
      
      // Check if console filter is active
      if (typeof window.filteredWarnings === 'undefined' && 
          typeof window.showFilteredWarnings !== 'function') {
        issues.push('Console filtering not active');
      }

      // Check filtered vs unfiltered messages
      const summary = this.getSummary();
      if (summary.filtered > 0) {
        issues.push(`${summary.filtered} unfiltered console messages`);
      }

      return issues;
    }

    checkPerformance() {
      const issues = [];
      
      // Check page load performance
      const navigation = performance.getEntriesByType('navigation')[0];
      if (navigation) {
        const loadTime = navigation.loadEventEnd - navigation.loadEventStart;
        if (loadTime > 3000) {
          issues.push(`Slow page load: ${loadTime}ms`);
        }
      }

      // Check for performance warnings
      const performanceIssues = this.getPerformanceIssues();
      if (performanceIssues.length > 0) {
        issues.push(`Performance issues: ${performanceIssues.length}`);
      }

      return issues;
    }

    // Reporting methods
    generateReport() {
      const summary = this.getSummary();
      const critical = this.getCriticalErrors();
      const moduleIssues = this.checkJavaScriptModules();
      const consoleIssues = this.checkConsoleFiltering();
      const performanceIssues = this.checkPerformance();

      return {
        summary,
        criticalErrors: critical,
        moduleIssues,
        consoleIssues,
        performanceIssues,
        recommendations: this.generateRecommendations(),
      };
    }

    generateRecommendations() {
      const recommendations = [];
      const summary = this.getSummary();

      if (summary.critical > 0) {
        recommendations.push('Fix critical JavaScript errors immediately');
      }

      if (summary.moduleErrors > 0) {
        recommendations.push('Check module imports and dependencies');
      }

      if (summary.performanceIssues > 0) {
        recommendations.push('Optimize performance bottlenecks');
      }

      if (summary.filtered > 0) {
        recommendations.push('Review and filter console messages');
      }

      return recommendations;
    }

    // Utility methods
    clearMessages() {
      this.messages = [];
      this.errors = [];
      this.warnings = [];
      this.logs = [];
      this.performanceIssues = [];
      this.moduleErrors = [];
    }

    exportData() {
      return {
        messages: this.messages,
        summary: this.getSummary(),
        report: this.generateReport(),
        timestamp: new Date().toISOString(),
        url: window.location.href,
      };
    }
  }

  // Initialize the debugger
  window.consoleDebugger = new ConsoleDebugger();

  // Add utility functions to window
  window.getConsoleSummary = () => window.consoleDebugger.getSummary();
  window.getCriticalErrors = () => window.consoleDebugger.getCriticalErrors();
  window.getFilteredMessages = () => window.consoleDebugger.getFilteredMessages();
  window.generateConsoleReport = () => window.consoleDebugger.generateReport();
  window.clearConsoleMessages = () => window.consoleDebugger.clearMessages();
  window.exportConsoleData = () => window.consoleDebugger.exportData();

  // Log that the debugger is active
  console.log('🔧 Console Debugger active. Use getConsoleSummary() to see results.');

})();
