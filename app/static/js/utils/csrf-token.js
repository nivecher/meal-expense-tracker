/**
 * CSRF Token Utility - TIGER-compliant
 * Single source of truth for CSRF token handling
 */

/**
 * Get CSRF token from meta tag or form input
 * @returns {string} CSRF token
 */
function get_csrf_token() {
  // Try meta tag first (preferred method)
  const meta_tag = document.querySelector('meta[name="csrf-token"]');
  if (meta_tag && meta_tag.getAttribute('content')) {
    return meta_tag.getAttribute('content');
  }

  // Fallback to form input
  const csrf_input = document.querySelector('input[name="csrf_token"]');
  if (csrf_input && csrf_input.value) {
    return csrf_input.value;
  }

  console.warn('CSRF token not found in DOM');
  return '';
}

/**
 * Get CSRF token for API requests
 * @returns {string} CSRF token
 */
function get_api_csrf_token() {
  const token = get_csrf_token();
  if (!token) {
    console.error('CSRF token not available for API request');
  }
  return token;
}

/**
 * Add CSRF token to headers object
 * @param {Headers|Object} headers - Headers object to modify
 * @returns {Headers|Object} Modified headers with CSRF token
 */
function add_csrf_to_headers(headers) {
  const token = get_api_csrf_token();
  if (token) {
    if (headers instanceof Headers) {
      headers.set('X-CSRFToken', token);
    } else {
      headers['X-CSRFToken'] = token;
    }
  }
  return headers;
}

// Export both naming conventions for compatibility
export {
  get_csrf_token,
  get_csrf_token as getCSRFToken,
  get_api_csrf_token,
  add_csrf_to_headers
};
