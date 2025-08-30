/**
 * CSRF Token Utility - TIGER-compliant
 * Single source of truth for CSRF token handling
 */

function get_csrf_token() {
  const csrf_input = document.querySelector('input[name="csrf_token"]');
  if (!csrf_input) {
    console.error('CSRF token not found in DOM');
    return '';
  }
  return csrf_input.value;
}

// Export both naming conventions for compatibility
export { get_csrf_token, get_csrf_token as getCSRFToken };
