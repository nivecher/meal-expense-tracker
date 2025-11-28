/**
 * Security Utilities
 *
 * Provides security-related utility functions for preventing XSS attacks
 * and sanitizing user input before DOM insertion.
 *
 * @version 1.0.0
 */

/**
 * Escape HTML special characters to prevent XSS attacks
 * Converts potentially dangerous characters to their HTML entity equivalents
 *
 * @param {string|null|undefined} text - Text to escape
 * @returns {string} - Escaped text safe for HTML insertion
 *
 * @example
 * escapeHtml('<script>alert("XSS")</script>')
 * // Returns: '&lt;script&gt;alert(&quot;XSS&quot;)&lt;&#x2F;script&gt;'
 */
function escapeHtml(text) {
  if (text === null || text === undefined) {
    return '';
  }

  const textString = String(text);
  const map = {
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#x27;',
    '/': '&#x2F;',
  };

  return textString.replace(/[&<>"'/]/g, (char) => map[char]);
}

/**
 * Safely set innerHTML by escaping the content
 * This is a convenience wrapper that combines escaping and DOM manipulation
 *
 * @param {HTMLElement} element - DOM element to update
 * @param {string} html - HTML content to set (will be escaped)
 *
 * @example
 * setSafeInnerHTML(element, userInput)
 */
function setSafeInnerHTML(element, html) {
  if (!element) {
    console.warn('setSafeInnerHTML: element is null or undefined');
    return;
  }

  element.innerHTML = escapeHtml(html);
}

// Export for ES6 modules
export { escapeHtml, setSafeInnerHTML };

// Export for CommonJS modules
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    escapeHtml,
    setSafeInnerHTML,
  };
}

// Make utilities available globally
window.SecurityUtils = {
  escapeHtml,
  setSafeInnerHTML,
};
