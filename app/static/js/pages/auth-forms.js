/**
 * Auth Forms Handler
 *
 * Handles authentication form submission, error logging, and validation display.
 * This replaces the inline JavaScript in the base_auth.html template.
 */

/**
 * Validate redirect URL to prevent open redirect vulnerabilities
 * Only allows relative URLs or same-origin absolute URLs
 * @param {string} url - URL to validate
 * @returns {string|null} - Validated URL or null if invalid
 */
function validateRedirectUrl(url) {
  if (!url || typeof url !== 'string') {
    return null;
  }

  // Allow relative URLs (starting with /)
  if (url.startsWith('/')) {
    // Ensure it doesn't contain protocol or host
    if (!url.includes('://') && !url.includes('//')) {
      return url;
    }
    return null;
  }

  // Allow same-origin absolute URLs only
  try {
    const urlObj = new URL(url, window.location.origin);
    if (urlObj.origin === window.location.origin) {
      return urlObj.pathname + urlObj.search + urlObj.hash;
    }
  } catch {
    // Invalid URL
  }

  return null;
}

// Helper function to display validation errors
function displayValidationErrors(form, errors) {
  // Clear existing errors
  form.querySelectorAll('.text-danger').forEach((el) => el.remove());
  form.querySelectorAll('.is-invalid').forEach((el) => el.classList.remove('is-invalid'));

  // Display new errors
  for (const [fieldName, errorMessages] of Object.entries(errors)) {
    const field = form.querySelector(`[name="${fieldName}"]`);
    if (field) {
      field.classList.add('is-invalid');
      const errorDiv = document.createElement('div');
      errorDiv.className = 'text-danger mt-1';
      errorDiv.textContent = Array.isArray(errorMessages) ? errorMessages[0] : errorMessages;
      field.parentNode.appendChild(errorDiv);
    }
  }
}

// Helper function to show error message
function showErrorMessage(message) {
  // Remove existing alerts
  document.querySelectorAll('.alert-danger').forEach((el) => el.remove());

  // Create new alert
  const alertDiv = document.createElement('div');
  alertDiv.className = 'alert alert-danger alert-dismissible fade show';

  // Append message as text node to prevent XSS - safely escape HTML
  alertDiv.appendChild(document.createTextNode(message));

  // Create and append close button separately
  const closeButton = document.createElement('button');
  closeButton.type = 'button';
  closeButton.className = 'btn-close';
  closeButton.setAttribute('data-bs-dismiss', 'alert');
  alertDiv.appendChild(closeButton);

  // Insert at the top of the form
  const form = document.querySelector('form');
  if (form) {
    form.insertBefore(alertDiv, form.firstChild);
  }
}

async function handleErrorResponse(response, form) {
  console.error('Response failed with status:', response.status);

  const contentType = response.headers.get('content-type');
  if (contentType && contentType.includes('application/json')) {
    try {
      const errorData = await response.json();
      console.error('Form validation errors:', errorData);

      // Display validation errors
      if (errorData.errors) {
        displayValidationErrors(form, errorData.errors);
      } else if (errorData.message) {
        showErrorMessage(errorData.message);
      }
      return;
    } catch (e) {
      console.error('Failed to parse error response:', e);
    }
  }

  console.error('Form submission failed:', response.status, response.statusText);
  // Don't reload to preserve error info for debugging
}

/**
 * Handle redirect from response data
 * @param {string} redirectUrl - URL to redirect to
 * @returns {boolean} - True if redirect was handled, false otherwise
 */
function handleRedirect(redirectUrl) {
  const validatedUrl = validateRedirectUrl(redirectUrl);
  if (validatedUrl) {
    window.location.href = validatedUrl;
    return true;
  }
  // Default to home page if redirect URL is invalid
  window.location.href = '/';
  return true;
}

/**
 * Handle successful JSON response
 * @param {Object} data - Response data
 * @returns {boolean} - True if response was handled, false otherwise
 */
function handleJsonResponse(data) {
  if (data.redirect) {
    handleRedirect(data.redirect);
    return true;
  }
  if (data.success) {
    window.location.reload();
    return true;
  }
  return false;
}

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
  } else {
    // Registration form not found - expected on login page
    console.debug('Registration form not found (expected on non-registration pages)');
  }

  // Simple form submission handler for auth forms
  const authForms = document.querySelectorAll('#login-form, #register-form');

  authForms.forEach((form) => {
    form.addEventListener('submit', async(_e) => {
      // Allow normal form submission for better reliability
      return;

      const submitBtn = form.querySelector('input[type="submit"], button[type="submit"]');
      const originalText = submitBtn.value || submitBtn.textContent;

      // Show loading state
      submitBtn.disabled = true;
      if (submitBtn.tagName === 'INPUT') {
        submitBtn.value = 'Processing...';
      } else {
        submitBtn.textContent = 'Processing...';
      }

      try {
        const formData = new FormData(form);

        // Include CSRF token only if available in form (local dev)
        const csrfInput = form.querySelector('input[name="csrf_token"]');
        if (csrfInput && csrfInput.value) {
          formData.set('csrf_token', csrfInput.value);
        } else {
          // For Lambda deployment, add empty CSRF token to satisfy form validation
          formData.set('csrf_token', '');
        }

        const url = form.action || window.location.pathname;

        const response = await fetch(url, {
          method: 'POST',
          body: formData,
          headers: {
            'X-Requested-With': 'XMLHttpRequest',
          },
        });

        // Check response status
        if (response.ok) {
          // Check if it's a redirect (successful login/registration)
          if (response.redirected || response.url !== window.location.href) {
            handleRedirect(response.url);
            return;
          }

          // Try to parse as JSON for API responses
          const contentType = response.headers.get('content-type');
          if (contentType && contentType.includes('application/json')) {
            const data = await response.json();
            if (handleJsonResponse(data)) {
              return;
            }
          }

          // For HTML responses, reload the page to show any messages
          window.location.reload();
        } else {
          await handleErrorResponse(response, form);
        }
      } catch (error) {
        console.error('Form submission error:', error);
        alert('An error occurred. Please try again.');
      } finally {
        // Restore button state
        submitBtn.disabled = false;
        if (submitBtn.tagName === 'INPUT') {
          submitBtn.value = originalText;
        } else {
          submitBtn.textContent = originalText;
        }
      }
    });
  });
});
