/**
 * Simple Logger - development vs production aware
 */

// Check if we're in development
const isDev = ['localhost', '127.0.0.1', ''].includes(window.location.hostname) ||
              window.location.port === '5000';

// Simple logging function
function log(level, ...args) {
  // In production, only log errors and warnings
  if (!isDev && !['error', 'warn'].includes(level)) return;

  const method = console[level] || console.log;
  method(...args);
}

// Logger object
const logger = {
  error: (...args) => log('error', ...args),
  warn: (...args) => log('warn', ...args),
  info: isDev ? (...args) => log('info', ...args) : () => {},
  debug: isDev ? (...args) => log('debug', ...args) : () => {},
  log: isDev ? (...args) => log('log', ...args) : () => {},
};

export { logger };
export default logger;
