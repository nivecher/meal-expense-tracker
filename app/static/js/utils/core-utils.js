/**
 * Core Utilities
 * Consolidated logging, error handling, and performance monitoring
 *
 * @module coreUtils
 * @version 2.0.0
 * @author Meal Expense Tracker Team
 */

// ===== LOGGER =====

const LOG_LEVELS = {
  ERROR: 'error',
  WARN: 'warn',
  INFO: 'info',
  DEBUG: 'debug',
  LOG: 'log',
};

// Determine if we're in development mode
const isDevelopment = window.location.hostname === 'localhost' ||
                     window.location.hostname === '127.0.0.1' ||
                     window.location.hostname === '' ||
                     window.location.port === '5000';

/**
 * Base logger function that handles all logging
 * @private
 * @param {string} level - The log level
 * @param {Array} args - Arguments to log
 */
function log(level, ...args) {
  // In production, only log errors and warnings
  if (!isDevelopment && !['error', 'warn'].includes(level)) {
    return;
  }

  const consoleMethod = console[level] || console.log;
  const logPrefix = console[level] ? '' : `[${level.toUpperCase()}] `;

  if (level === 'error' || level === 'warn' || isDevelopment) {
    consoleMethod.apply(console, [logPrefix, ...args]);
  }
}

// Create logger methods
const logger = {
  error: (...args) => log('error', ...args),
  warn: (...args) => log('warn', ...args),
  info: isDevelopment ? (...args) => log('info', ...args) : () => {},
  debug: isDevelopment ? (...args) => log('debug', ...args) : () => {},
  log: isDevelopment ? (...args) => log('log', ...args) : () => {},

  isEnabled(level) {
    if (isDevelopment) return true;
    return ['error', 'warn'].includes(level);
  },
};

// ===== SIMPLE ERROR HANDLER =====

/**
 * Simple error handler for common use cases
 */
const errorHandler = {
  /**
   * Wrap a function with basic error handling
   * @param {Function} fn - Function to wrap
   * @param {string} context - Context for error reporting
   * @returns {Function} Wrapped function
   */
  wrap(fn, context = 'unknown') {
    return async(...args) => {
      try {
        return await fn(...args);
      } catch (error) {
        logger.error(`Error in ${context}:`, error);

        // Show user-friendly error if needed
        if (typeof window !== 'undefined' && window.showErrorToast) {
          window.showErrorToast('An error occurred. Please try again.');
        }

        throw error;
      }
    };
  },

  /**
   * Handle error with optional retry
   * @param {Error} error - Error that occurred
   * @param {string} context - Context where error occurred
   * @param {Function} retryFn - Optional retry function
   */
  handle(error, context, retryFn = null) {
    logger.error(`Error in ${context}:`, error);

    // Optionally retry
    if (retryFn && typeof retryFn === 'function') {
      setTimeout(() => {
        try {
          retryFn();
        } catch (retryError) {
          logger.error(`Retry failed in ${context}:`, retryError);
        }
      }, 1000);
    }
  },
};

// ===== SIMPLE PERFORMANCE MONITOR =====

/**
 * Lightweight performance monitoring
 */
const performance = {
  /**
   * Measure function execution time
   * @param {string} name - Name of the measurement
   * @param {Function} fn - Function to measure
   * @returns {Function} Wrapped function
   */
  measure(name, fn) {
    return async(...args) => {
      const start = window.performance.now();
      try {
        const result = await fn(...args);
        const duration = window.performance.now() - start;
        logger.debug(`${name} took ${duration.toFixed(2)}ms`);
        return result;
      } catch (error) {
        const duration = window.performance.now() - start;
        logger.debug(`${name} failed after ${duration.toFixed(2)}ms`);
        throw error;
      }
    };
  },

  /**
   * Mark a performance milestone
   * @param {string} name - Name of the milestone
   */
  mark(name) {
    if (window.performance && window.performance.mark) {
      window.performance.mark(name);
      logger.debug(`Performance mark: ${name}`);
    }
  },

  /**
   * Measure time between two marks
   * @param {string} name - Name of the measurement
   * @param {string} startMark - Start mark name
   * @param {string} endMark - End mark name
   */
  measureBetween(name, startMark, endMark) {
    if (window.performance && window.performance.measure) {
      try {
        window.performance.measure(name, startMark, endMark);
        const measurement = window.performance.getEntriesByName(name)[0];
        if (measurement) {
          logger.debug(`${name}: ${measurement.duration.toFixed(2)}ms`);
        }
      } catch (error) {
        logger.debug(`Could not measure ${name}:`, error);
      }
    }
  },
};

// ===== UTILITY FUNCTIONS =====

/**
 * Debounce function calls
 * @param {Function} func - Function to debounce
 * @param {number} wait - Wait time in milliseconds
 * @param {boolean} immediate - Execute immediately
 * @returns {Function} Debounced function
 */
function debounce(func, wait, immediate = false) {
  let timeout;
  return function executedFunction(...args) {
    const later = () => {
      timeout = null;
      if (!immediate) func(...args);
    };
    const callNow = immediate && !timeout;
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
    if (callNow) func(...args);
  };
}

/**
 * Throttle function calls
 * @param {Function} func - Function to throttle
 * @param {number} limit - Time limit in milliseconds
 * @returns {Function} Throttled function
 */
function throttle(func, limit) {
  let inThrottle;
  return function(...args) {
    if (!inThrottle) {
      func.apply(this, args);
      inThrottle = true;
      setTimeout(() => {
        inThrottle = false;
      }, limit);
    }
  };
}

/**
 * Simple delay function
 * @param {number} ms - Milliseconds to delay
 * @returns {Promise} Promise that resolves after delay
 */
function delay(ms) {
  return new Promise((resolve) => {
    setTimeout(resolve, ms);
  });
}

/**
 * Retry a function with exponential backoff
 * @param {Function} fn - Function to retry
 * @param {number} maxAttempts - Maximum retry attempts
 * @param {number} baseDelay - Base delay in milliseconds
 * @returns {Promise} Promise that resolves with function result
 */
async function retry(fn, maxAttempts = 3, baseDelay = 1000) {
  for (let attempt = 1; attempt <= maxAttempts; attempt++) {
    try {
      return await fn();
    } catch (error) {
      if (attempt === maxAttempts) {
        throw error;
      }

      const delayTime = baseDelay * Math.pow(2, attempt - 1);
      logger.debug(`Attempt ${attempt} failed, retrying in ${delayTime}ms`);
      await delay(delayTime);
    }
  }
}

// ===== EXPORTS =====

export {
  logger,
  LOG_LEVELS,
  errorHandler,
  performance,
  debounce,
  throttle,
  delay,
  retry,
};

// Default export for backward compatibility
export default {
  logger,
  LOG_LEVELS,
  errorHandler,
  performance,
  debounce,
  throttle,
  delay,
  retry,
};
