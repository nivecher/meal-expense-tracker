/**
 * Timezone Handler Utility
 *
 * Detects browser timezone and stores it in a cookie for server-side use.
 * This ensures the browser timezone is available for date/time display
 * even when not submitting forms.
 */

/**
 * Detect browser timezone using Intl API.
 * @returns {string} IANA timezone string (e.g., 'America/New_York') or 'UTC' as fallback
 */
function detectBrowserTimezone() {
  try {
    if (typeof Intl !== 'undefined' && Intl.DateTimeFormat) {
      // eslint-disable-next-line new-cap
      const options = Intl.DateTimeFormat().resolvedOptions();
      if (options && options.timeZone && typeof options.timeZone === 'string') {
        return options.timeZone;
      }
    }
  } catch (error) {
    console.warn('Timezone detection failed:', error);
  }
  return 'UTC';
}

/**
 * Set a cookie with the browser timezone.
 * @param {string} timezone - The timezone string to store
 * @param {number} days - Number of days until cookie expires (default: 365)
 */
function setTimezoneCookie(timezone, days = 365) {
  const expires = new Date();
  expires.setTime(expires.getTime() + days * 24 * 60 * 60 * 1000);
  const expiresStr = expires.toUTCString();
  // For CORS compatibility: use SameSite=None; Secure in HTTPS environments
  // This ensures cookies work when CloudFront proxies to API Gateway
  const isHttps = window.location.protocol === 'https:';
  const sameSite = isHttps ? 'SameSite=None' : 'SameSite=Lax';
  const secureFlag = isHttps ? '; Secure' : '';
  document.cookie = `browser_timezone=${encodeURIComponent(timezone)}; expires=${expiresStr}; path=/; ${sameSite}${secureFlag}`;
}

/**
 * Initialize timezone handling on page load.
 * Stores timezone in cookie so server can use it for form initialization.
 * Display formatting is handled client-side by date-formatter.js.
 */
function initializeTimezoneHandler() {
  const detectedTimezone = detectBrowserTimezone();
  setTimezoneCookie(detectedTimezone);
  console.log('Browser timezone detected and stored:', detectedTimezone);
}

// Initialize on DOM load
document.addEventListener('DOMContentLoaded', initializeTimezoneHandler);

// Also initialize immediately if DOM is already loaded
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initializeTimezoneHandler);
} else {
  initializeTimezoneHandler();
}

// Export for use in other modules
export { detectBrowserTimezone, setTimezoneCookie, initializeTimezoneHandler };
