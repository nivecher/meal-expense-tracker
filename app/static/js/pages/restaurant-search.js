/**
 * Restaurant Search Page
 *
 * Handles auto-submit form functionality and cookie management for restaurant search.
 * This replaces the inline JavaScript in the restaurants/search.html template.
 */

document.addEventListener('DOMContentLoaded', () => {
  // Cookie utility function
  function setCookie(name, value, days = 365) {
    const expires = new Date();
    expires.setTime(expires.getTime() + days * 24 * 60 * 60 * 1000);
    // For CORS compatibility: use SameSite=None; Secure in HTTPS environments
    // This ensures cookies work when CloudFront proxies to API Gateway
    const isHttps = window.location.protocol === 'https:';
    const sameSite = isHttps ? 'SameSite=None' : 'SameSite=Lax';
    const secureFlag = isHttps ? '; Secure' : '';
    document.cookie = `${name}=${value};expires=${expires.toUTCString()};path=/;${sameSite}${secureFlag}`;
  }

  const form = document.querySelector('form');
  if (form) {
    form.querySelectorAll('select').forEach((select) => {
      select.addEventListener('change', () => {
        // Save page size preference to cookie if it's the per_page selector
        if (select.name === 'per_page') {
          setCookie('restaurant_page_size', select.value);
        }
        form.submit();
      });
    });
  }
});
