/**
 * Simple Error Handler
 *
 * Provides basic error handling without interfering with console methods
 * or filtering messages.
 *
 * @version 2.0.0
 * @author Meal Expense Tracker Team
 */

class ErrorHandler {
  constructor(options = {}) {
    this.options = {
      enableErrorReporting: true,
      maxErrors: 100,
      ...options,
    };

    this.errorCount = 0;
    this.errors = [];

    if (this.options.enableErrorReporting) {
      this.setupErrorHandlers();
    }
  }

  setupErrorHandlers() {
    // Global error handler - only log, don't interfere
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

    // Resource loading error handler - only for actual resource failures
    window.addEventListener('error', (event) => {
      if (event.target !== window) {
        const resourceUrl = event.target.src || event.target.href || '';

        // Only log actual resource loading errors, not navigation
        const isRootUrl = resourceUrl === window.location.origin ||
                         resourceUrl === `${window.location.origin}/` ||
                         resourceUrl === window.location.href;
        const isEmptyOrInvalid = !resourceUrl || resourceUrl.startsWith('data:');

        if (!isRootUrl && !isEmptyOrInvalid) {
          this.handleError({
            type: 'resource',
            message: `Failed to load resource: ${resourceUrl}`,
            element: event.target,
          });
        }
      }
    }, true);
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

    // Only log in development mode
    if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
      console.group('🚨 Application Error');
      console.error('Type:', errorInfo.type);
      console.error('Message:', errorInfo.message);
      console.error('Timestamp:', new Date().toISOString());
      if (errorInfo.filename) console.error('File:', errorInfo.filename);
      if (errorInfo.lineno) console.error('Line:', errorInfo.lineno);
      console.groupEnd();
    }
  }

  getErrorStats() {
    return {
      totalErrors: this.errorCount,
      recentErrors: this.errors.slice(-10),
    };
  }

  clearErrors() {
    this.errors = [];
    this.errorCount = 0;
    console.log('✅ Error logs cleared');
  }

  exportErrorReport() {
    const report = {
      timestamp: new Date().toISOString(),
      userAgent: navigator.userAgent,
      url: window.location.href,
      errors: this.errors,
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
  enableErrorReporting: true,
});

// Export for module usage
export default ErrorHandler;
export { errorHandler };
