/**
 * Client-side Date Formatter Utility
 *
 * Formats UTC ISO 8601 timestamps in the browser's timezone.
 * This is more efficient than server-side timezone conversion.
 */

/**
 * Format a date with a custom format string (Python strftime-like).
 * @param {Date} date - JavaScript Date object
 * @param {string} format - Format string with % placeholders
 * @returns {string} Formatted date string
 */
function formatCustomDate(date, format) {
  const monthNames = [
    'January', 'February', 'March', 'April', 'May', 'June',
    'July', 'August', 'September', 'October', 'November', 'December',
  ];
  const monthNamesShort = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  const dayNames = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
  const dayNamesShort = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];

  let result = format;
  const month = date.getMonth();
  const day = date.getDate();
  const year = date.getFullYear();
  const hours = date.getHours();
  const minutes = date.getMinutes();
  const seconds = date.getSeconds();
  const dayOfWeek = date.getDay();

  // Replace format codes
  result = result.replace(/%Y/g, String(year));
  result = result.replace(/%y/g, String(year).slice(-2));
  result = result.replace(/%m/g, String(month + 1).padStart(2, '0'));
  result = result.replace(/%B/g, monthNames[month]);
  result = result.replace(/%b/g, monthNamesShort[month]);
  result = result.replace(/%d/g, String(day).padStart(2, '0'));
  result = result.replace(/%A/g, dayNames[dayOfWeek]);
  result = result.replace(/%a/g, dayNamesShort[dayOfWeek]);
  result = result.replace(/%H/g, String(hours).padStart(2, '0'));
  result = result.replace(/%I/g, String(hours % 12 || 12).padStart(2, '0'));
  result = result.replace(/%M/g, String(minutes).padStart(2, '0'));
  result = result.replace(/%S/g, String(seconds).padStart(2, '0'));
  result = result.replace(/%p/g, hours >= 12 ? 'PM' : 'AM');

  return result;
}

/**
 * Format a UTC ISO 8601 datetime string to the browser's local timezone.
 * @param {string} isoString - UTC ISO 8601 datetime string (e.g., '2024-01-15T14:30:00Z')
 * @param {Object} options - Intl.DateTimeFormat options
 * @returns {string} Formatted datetime string
 */
function formatDateTime(isoString, options = {}) {
  if (!isoString) {
    return 'Never';
  }

  try {
    const date = new Date(isoString);
    if (Number.isNaN(date.getTime())) {
      return 'Invalid date';
    }

    const defaultOptions = {
      dateStyle: 'medium',
      timeStyle: 'short',
      timeZone: new Intl.DateTimeFormat().resolvedOptions().timeZone,
    };

    const formatOptions = { ...defaultOptions, ...options };
    return new Intl.DateTimeFormat('en-US', formatOptions).format(date);
  } catch (error) {
    console.warn('Date formatting failed:', error);
    return 'Invalid date';
  }
}

/**
 * Format a UTC ISO 8601 datetime string as a date only.
 * @param {string} isoString - UTC ISO 8601 datetime string
 * @param {string} format - Format style: 'short', 'medium', 'long', 'full', or custom format string
 * @returns {string} Formatted date string
 */
function formatDate(isoString, format = 'medium') {
  if (!isoString) {
    return 'Never';
  }

  try {
    const date = new Date(isoString);
    if (Number.isNaN(date.getTime())) {
      return 'Invalid date';
    }

    const formatMap = {
      short: { dateStyle: 'short' },
      medium: { dateStyle: 'medium' },
      long: { dateStyle: 'long' },
      full: { dateStyle: 'full' },
    };

    // Custom format string (e.g., '%b %d, %Y')
    if (format.includes('%')) {
      return formatCustomDate(date, format);
    }

    const options = formatMap[format] || formatMap.medium;
    return new Intl.DateTimeFormat('en-US', options).format(date);
  } catch (error) {
    console.warn('Date formatting failed:', error);
    return 'Invalid date';
  }
}

/**
 * Format a relative time string (e.g., "2 hours ago").
 * @param {string} isoString - UTC ISO 8601 datetime string
 * @returns {string} Relative time string
 */
function formatTimeAgo(isoString) {
  if (!isoString) {
    return 'Never';
  }

  try {
    const date = new Date(isoString);
    if (Number.isNaN(date.getTime())) {
      return 'Invalid date';
    }

    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffSeconds = Math.floor(diffMs / 1000);
    const diffMinutes = Math.floor(diffSeconds / 60);
    const diffHours = Math.floor(diffMinutes / 60);
    const diffDays = Math.floor(diffHours / 24);
    const diffMonths = Math.floor(diffDays / 30);
    const diffYears = Math.floor(diffDays / 365);

    if (diffYears > 0) {
      return `${diffYears} year${diffYears > 1 ? 's' : ''} ago`;
    }
    if (diffMonths > 0) {
      return `${diffMonths} month${diffMonths > 1 ? 's' : ''} ago`;
    }
    if (diffDays > 0) {
      return `${diffDays} day${diffDays > 1 ? 's' : ''} ago`;
    }
    if (diffHours > 0) {
      return `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`;
    }
    if (diffMinutes > 0) {
      return `${diffMinutes} minute${diffMinutes > 1 ? 's' : ''} ago`;
    }
    return 'Just now';
  } catch (error) {
    console.warn('Time ago formatting failed:', error);
    return 'Unknown time';
  }
}

/**
 * Initialize date formatting for all elements with data-datetime attributes.
 * This should be called on page load.
 */
function initializeDateFormatting() {
  // Format all elements with data-datetime attribute
  document.querySelectorAll('[data-datetime]').forEach((el) => {
    const isoString = el.dataset.datetime;
    const format = el.dataset.datetimeFormat || 'medium';
    const formatType = el.dataset.datetimeType || 'date'; // 'date', 'datetime', or 'timeago'

    let formatted;
    if (formatType === 'timeago') {
      formatted = formatTimeAgo(isoString);
    } else if (formatType === 'datetime') {
      formatted = formatDateTime(isoString, { dateStyle: 'medium', timeStyle: 'short' });
    } else {
      formatted = formatDate(isoString, format);
    }

    el.textContent = formatted;
  });
}

// Initialize on DOM load
document.addEventListener('DOMContentLoaded', initializeDateFormatting);

// Also initialize immediately if DOM is already loaded
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initializeDateFormatting);
} else {
  initializeDateFormatting();
}

// Export for use in other modules
export { formatDateTime, formatDate, formatTimeAgo, formatCustomDate, initializeDateFormatting };
