/**
 * Logger Utility
 *
 * Provides consistent logging throughout the application with environment-aware behavior.
 * In production, only error and warn levels are logged by default.
 * In development, all log levels are enabled.
 */

// Log levels
const LOG_LEVELS = {
  ERROR: 'error',
  WARN: 'warn',
  INFO: 'info',
  DEBUG: 'debug',
  LOG: 'log',
};

// Determine if we're in development mode (check URL for localhost or 127.0.0.1)
const isDevelopment = window.location.hostname === 'localhost' ||
                     window.location.hostname === '127.0.0.1' ||
                     window.location.hostname === '' ||
                     window.location.port === '5001'; // Default Flask port

/**
 * Base logger function that handles all logging
 * @private
 * @param {string} level - The log level (error, warn, info, debug, log)
 * @param {Array} args - Arguments to log
 */
function log (level, ...args) {
  // In production, only log errors and warnings
  if (!isDevelopment && !['error', 'warn'].includes(level)) {
    return;
  }

  // Use the appropriate console method if it exists
  const consoleMethod = console[level] || console.log;
  const logPrefix = console[level] ? '' : `[${level.toUpperCase()}] `;

  // Only log in development or for error/warn levels in production
  if (level === 'error' || level === 'warn' || isDevelopment) {
    // Use Function.prototype.apply to handle the console method call properly
    consoleMethod.apply(console, [logPrefix, ...args]);
  }
}

// Create logger methods for each log level
const logger = {
  error: (...args) => log('error', ...args),
  warn: (...args) => log('warn', ...args),
  info: isDevelopment ? (...args) => log('info', ...args) : () => {},
  debug: isDevelopment ? (...args) => log('debug', ...args) : () => {},
  log: isDevelopment ? (...args) => log('log', ...args) : () => {},

  /**
   * Check if a log level is enabled
   * @param {string} level - The log level to check
   * @returns {boolean} True if the log level is enabled
   */
  isEnabled (level) {
    if (isDevelopment) return true;
    return ['error', 'warn'].includes(level);
  },
};

export { logger, LOG_LEVELS };

export default logger;
