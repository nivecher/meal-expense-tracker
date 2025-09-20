/**
 * Auth Forms Handler
 *
 * Handles authentication form submission, error logging, and validation display.
 * This replaces the inline JavaScript in the base_auth.html template.
 */

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
  alertDiv.innerHTML = `
    ${message}
    <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
  `;

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
            window.location.href = response.url;
            return;
          }

          // Try to parse as JSON for API responses
          const contentType = response.headers.get('content-type');
          if (contentType && contentType.includes('application/json')) {
            const data = await response.json();
            if (data.redirect) {
              window.location.href = data.redirect;
              return;
            }
            if (data.success) {
              window.location.reload();
              return;
            }
          }

          // For HTML responses, reload the page to show any messages
          window.location.reload();
        } else {
          await handleErrorResponse(response, form);
        }
      } catch {
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
