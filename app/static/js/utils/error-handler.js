/**
 * Enhanced Error Handler
 *
 * Provides comprehensive error handling and console management
 * for the Meal Expense Tracker application.
 *
 * @version 1.0.0
 * @author Meal Expense Tracker Team
 */

class ErrorHandler {
  constructor(options = {}) {
    this.options = {
      enableConsoleFilter: true,
      enableErrorReporting: true,
      enablePerformanceMonitoring: true,
      logLevel: 'warn', // 'error', 'warn', 'info', 'debug'
      maxErrors: 100,
      ...options,
    };

    this.errorCount = 0;
    this.errors = [];
    this.performanceMetrics = new Map();

    this.init();
  }

  init() {
    if (this.options.enableConsoleFilter) {
      this.setupConsoleFilter();
    }

    if (this.options.enableErrorReporting) {
      this.setupErrorHandlers();
    }

    if (this.options.enablePerformanceMonitoring) {
      this.setupPerformanceMonitoring();
    }

    this.setupGlobalUtilities();
  }

  setupConsoleFilter() {
    // Store original console methods
    const originalConsole = {
      log: console.log,
      warn: console.warn,
      error: console.error,
      info: console.info,
      debug: console.debug,
    };

    // Filter patterns for common external library warnings
    const filteredPatterns = [
      // Bootstrap warnings
      /Bootstrap.*deprecated/i,
      /Bootstrap.*warning/i,
      /Bootstrap.*v5/i,

      // jQuery warnings
      /jQuery.*deprecated/i,
      /jQuery.*warning/i,

      // Font Awesome warnings
      /Font Awesome.*deprecated/i,
      /Font Awesome.*warning/i,
      /Font Awesome.*v6/i,

      // Select2 warnings
      /Select2.*deprecated/i,
      /Select2.*warning/i,

      // Chart.js warnings
      /Chart\.js.*deprecated/i,
      /Chart\.js.*warning/i,

      // CDN warnings
      /cdn\.jsdelivr\.net/i,
      /cdnjs\.cloudflare\.com/i,
      /code\.jquery\.com/i,

      // Browser compatibility warnings
      /webkit.*not supported/i,
      /text-size-adjust.*not supported/i,
      /color-adjust.*not supported/i,
      /CSS.*not supported/i,

      // Extension warnings
      /chrome-extension/i,
      /moz-extension/i,
      /safari-extension/i,
    ];

    // Check if message should be filtered
    const shouldFilter = (message) => {
      if (typeof message !== 'string') return false;
      return filteredPatterns.some((pattern) => pattern.test(message));
    };

    // Override console methods
    console.warn = (...args) => {
      if (shouldFilter(args[0])) {
        this.logFilteredMessage('warn', args[0]);
        return;
      }
      originalConsole.warn.apply(console, args);
    };

    console.error = (...args) => {
      if (shouldFilter(args[0])) {
        this.logFilteredMessage('error', args[0]);
        return;
      }
      this.logError(args[0], args[1]);
      originalConsole.error.apply(console, args);
    };

    console.log = (...args) => {
      if (shouldFilter(args[0])) {
        this.logFilteredMessage('log', args[0]);
        return;
      }
      originalConsole.log.apply(console, args);
    };
  }

  setupErrorHandlers() {
    // Global error handler
    window.addEventListener('error', (event) => {
      this.handleError({
        type: 'javascript',
        message: event.message,
        filename: event.filename,
        lineno: event.lineno,
        colno: event.colno,
        error: event.error,
      });
    });

    // Unhandled promise rejection handler
    window.addEventListener('unhandledrejection', (event) => {
      this.handleError({
        type: 'promise',
        message: event.reason?.message || 'Unhandled promise rejection',
        error: event.reason,
      });
    });

    // Resource loading error handler
    window.addEventListener('error', (event) => {
      if (event.target !== window) {
        this.handleError({
          type: 'resource',
          message: `Failed to load resource: ${event.target.src || event.target.href}`,
          element: event.target,
        });
      }
    }, true);
  }

  setupPerformanceMonitoring() {
    // Monitor long tasks
    if ('PerformanceObserver' in window) {
      try {
        const observer = new PerformanceObserver((list) => {
          for (const entry of list.getEntries()) {
            if (entry.duration > 50) { // Tasks longer than 50ms
              this.logPerformanceIssue('long-task', {
                duration: entry.duration,
                startTime: entry.startTime,
              });
            }
          }
        });
        observer.observe({ entryTypes: ['longtask'] });
      } catch {
        console.warn('Performance monitoring not available:', error);
      }
    }

    // Monitor memory usage
    if ('memory' in performance) {
      setInterval(() => {
        const { memory } = performance;
        if (memory.usedJSHeapSize > memory.jsHeapSizeLimit * 0.9) {
          this.logPerformanceIssue('high-memory', {
            used: memory.usedJSHeapSize,
            limit: memory.jsHeapSizeLimit,
            percentage: (memory.usedJSHeapSize / memory.jsHeapSizeLimit) * 100,
          });
        }
      }, 30000); // Check every 30 seconds
    }
  }

  setupGlobalUtilities() {
    // Add utility functions to window
    window.errorHandler = this;
    window.getErrorStats = () => this.getErrorStats();
    window.clearErrors = () => this.clearErrors();
    window.showFilteredMessages = () => this.showFilteredMessages();
    window.exportErrorReport = () => this.exportErrorReport();
  }

  handleError(errorInfo) {
    this.errorCount++;

    if (this.errors.length < this.options.maxErrors) {
      this.errors.push({
        ...errorInfo,
        timestamp: new Date().toISOString(),
        userAgent: navigator.userAgent,
        url: window.location.href,
      });
    }

    // Show user-friendly error message
    if (window.showErrorToast) {
      window.showErrorToast('An error occurred. Please try again.');
    }

    // Log to console in development
    if (this.options.logLevel === 'debug') {
      console.group('🚨 Application Error');
      console.error('Type:', errorInfo.type);
      console.error('Message:', errorInfo.message);
      console.error('Timestamp:', new Date().toISOString());
      if (errorInfo.filename) console.error('File:', errorInfo.filename);
      if (errorInfo.lineno) console.error('Line:', errorInfo.lineno);
      console.groupEnd();
    }
  }

  logError(message, error) {
    this.handleError({
      type: 'console',
      message,
      error,
    });
  }

  logFilteredMessage(type, message) {
    if (!window.filteredMessages) {
      window.filteredMessages = [];
    }

    window.filteredMessages.push({
      type,
      message,
      timestamp: new Date().toISOString(),
    });
  }

  logPerformanceIssue(type, data) {
    this.performanceMetrics.set(type, {
      ...data,
      timestamp: new Date().toISOString(),
    });

    if (this.options.logLevel === 'debug') {
      console.warn(`Performance issue: ${type}`, data);
    }
  }

  getErrorStats() {
    return {
      totalErrors: this.errorCount,
      recentErrors: this.errors.slice(-10),
      performanceIssues: Array.from(this.performanceMetrics.entries()),
      filteredMessages: window.filteredMessages?.length || 0,
    };
  }

  clearErrors() {
    this.errors = [];
    this.errorCount = 0;
    this.performanceMetrics.clear();
    if (window.filteredMessages) {
      window.filteredMessages = [];
    }
    console.log('✅ Error logs cleared');
  }

  showFilteredMessages() {
    const messages = window.filteredMessages || [];
    console.group('🔍 Filtered Console Messages');
    messages.forEach((msg, index) => {
      console.log(`${index + 1}. [${msg.type.toUpperCase()}] ${msg.message}`);
    });
    console.groupEnd();
    return messages.length;
  }

  exportErrorReport() {
    const report = {
      timestamp: new Date().toISOString(),
      userAgent: navigator.userAgent,
      url: window.location.href,
      errors: this.errors,
      performanceIssues: Array.from(this.performanceMetrics.entries()),
      filteredMessages: window.filteredMessages || [],
    };

    const blob = new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `error-report-${Date.now()}.json`;
    a.click();
    URL.revokeObjectURL(url);

    return report;
  }
}

// Initialize error handler
const errorHandler = new ErrorHandler({
  enableConsoleFilter: true,
  enableErrorReporting: true,
  enablePerformanceMonitoring: true,
  logLevel: window.location.hostname === 'localhost' ? 'debug' : 'warn',
});

// Export for module usage
export default ErrorHandler;
export { errorHandler };
