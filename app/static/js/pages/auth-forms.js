/**
 * Auth Forms Handler
 *
 * Handles authentication form submission, error logging, and validation display.
 * This replaces the inline JavaScript in the base_auth.html template.
 */

/**
 * Detect browser timezone using Intl API.
 * This is the standard, non-intrusive way to detect user timezone.
 *
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
 * Set timezone in registration form.
 * Called on page load and before form submission.
 */
function setTimezoneForRegistration() {
  const timezoneInput = document.getElementById('timezone');
  const registerForm = document.getElementById('register-form');

  if (timezoneInput && registerForm) {
    const detectedTimezone = detectBrowserTimezone();
    timezoneInput.value = detectedTimezone;
    console.log('Timezone set:', detectedTimezone);
    return true;
  }

  console.warn('Could not set timezone: form or input not found');
  return false;
}

document.addEventListener('DOMContentLoaded', () => {
  // Add error logging that persists across redirects
  window.addEventListener('error', (e) => {
    console.error('Global error:', e.error, e.filename, e.lineno);
    localStorage.setItem(
      'lastError',
      JSON.stringify({
        error: e.error?.toString(),
        filename: e.filename,
        lineno: e.lineno,
        timestamp: new Date().toISOString(),
      }),
    );
  });

  // Check for previous errors
  const lastError = localStorage.getItem('lastError');
  if (lastError) {
    console.log('Previous error found:', lastError);
    // Clear it after logging
    localStorage.removeItem('lastError');
  }

  // Detect and set timezone for registration form
  const registerForm = document.getElementById('register-form');
  if (registerForm) {
    // Set timezone immediately
    const wasSet = setTimezoneForRegistration();
    if (wasSet) {
      console.log('✅ Timezone detection initialized for registration form');
    } else {
      console.error('❌ Failed to initialize timezone detection');
    }

    // Also set timezone right before form submission as backup
    registerForm.addEventListener(
      'submit',
      (_event) => {
        const tzInput = document.getElementById('timezone');
        if (tzInput) {
          const tz = detectBrowserTimezone();
          tzInput.value = tz;
          console.log('🔄 Timezone updated before submit:', tz);
          console.log('📋 Form data includes timezone:', tzInput.value);
        } else {
          console.error('❌ Timezone input not found on submit!');
        }
      },
      true, // Use capture phase to ensure it runs before form submits
    );
  }
  // Registration form not found - expected on login page (no logging needed)

  // Simple form submission handler for auth forms
  const authForms = document.querySelectorAll('#login-form, #register-form');

  authForms.forEach((form) => {
    form.addEventListener('submit', async(_e) => {
      // Allow normal form submission for better reliability
      // Note: AJAX form submission code removed to use standard form submission
      // This ensures better compatibility and reliability
    });
  });
});
