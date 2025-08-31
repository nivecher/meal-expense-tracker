/**
 * Authentication forms handler
 * Handles registration and login form functionality
 */

// Get CSRF token from meta tag or form
function getCSRFToken() {
  // Try meta tag first
  const metaToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
  if (metaToken) return metaToken;

  // Try form input
  const formToken = document.querySelector('input[name="csrf_token"]')?.value;
  if (formToken) return formToken;

  console.warn('CSRF token not found');
  return null;
}



// Set field error with Bootstrap styling
function setFieldError(fieldName, message) {
  const field = document.querySelector(`input[name="${fieldName}"]`);
  if (!field) return;

  field.classList.add('is-invalid');

  const feedback = document.createElement('div');
  feedback.className = 'invalid-feedback';
  feedback.textContent = message;

  field.parentNode.appendChild(feedback);
}

// Enhanced form validation specific to auth forms
function enhanceAuthFormValidation(form) {
  // Custom validation messages for auth forms
  const inputs = form.querySelectorAll('input[required]');
  inputs.forEach(input => {
    input.addEventListener('invalid', (e) => {
      e.preventDefault();

      let message = '';
      if (input.validity.valueMissing) {
        switch (input.name) {
          case 'username':
            message = 'Please enter your username';
            break;
          case 'email':
            message = 'Please enter your email address';
            break;
          case 'password':
            message = 'Please enter your password';
            break;
          case 'password2':
            message = 'Please confirm your password';
            break;
          default:
            message = 'This field is required';
        }
      } else if (input.validity.typeMismatch && input.type === 'email') {
        message = 'Please enter a valid email address';
      }

      if (message) {
        setFieldError(input.name, message);
      }
    });
  });
}



// Initialize auth forms - enhanced validation for auth-specific needs
export function init() {
  console.log('Initializing auth forms...');

  // Find authentication forms specifically
  const authForms = document.querySelectorAll('#login-form, #register-form');

  authForms.forEach(form => {
    // Add enhanced validation for auth forms
    enhanceAuthFormValidation(form);

    form.querySelectorAll('input').forEach(input => {
      input.addEventListener('blur', () => {
        // Clear previous errors on focus out
        input.classList.remove('is-invalid');
        const feedback = input.parentNode.querySelector('.invalid-feedback');
        if (feedback) feedback.remove();
      });

      // Add real-time validation for auth fields
      if (input.name === 'password2') {
        input.addEventListener('input', () => {
          const password = form.querySelector('input[name="password"]')?.value;
          if (password && input.value && password !== input.value) {
            setFieldError('password2', 'Passwords do not match');
          } else {
            input.classList.remove('is-invalid');
            const feedback = input.parentNode.querySelector('.invalid-feedback');
            if (feedback) feedback.remove();
          }
        });
      }
    });
  });

  // Ensure CSRF tokens are present (the existing form system should handle this)
  const csrfToken = getCSRFToken();
  if (csrfToken) {
    authForms.forEach(form => {
      let csrfInput = form.querySelector('input[name="csrf_token"]');
      if (!csrfInput) {
        csrfInput = document.createElement('input');
        csrfInput.type = 'hidden';
        csrfInput.name = 'csrf_token';
        form.appendChild(csrfInput);
        csrfInput.value = csrfToken;
      }
    });
  }

  console.log(`Auth forms enhanced for ${authForms.length} forms`);
}
