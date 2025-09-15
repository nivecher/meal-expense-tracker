/**
 * Simple form utilities without over-engineering
 */

import { validateField, showFormValidationErrors } from './validation.js';
import { handleAjaxFormSubmit, setFormLoading } from './submission.js';

// Set up real-time validation
function setupRealTimeValidation(form) {
  form.querySelectorAll('input, select, textarea').forEach((input) => {
    input.addEventListener('input', () => validateField(input));
  });
}

// Handle form validation on submit
function handleFormValidation(event) {
  const form = event.target;
  if (!form.checkValidity()) {
    event.preventDefault();
    event.stopPropagation();
    showFormValidationErrors(form);
  }
  form.classList.add('was-validated');
}

// Set up form validation
function setupFormValidation(form) {
  form.setAttribute('novalidate', '');
  form.addEventListener('submit', handleFormValidation);
  setupRealTimeValidation(form);
}

// Handle form submission
async function handleFormSubmit(event) {
  const form = event.target.closest('form');
  if (!form || form.classList.contains('is-submitting')) {
    event.preventDefault();
    return;
  }

  // Skip auth forms - let them submit normally
  if (form.id === 'login-form' || form.id === 'register-form') {
    return;
  }

  // Check for confirmation
  const confirmMessage = form.getAttribute('data-confirm');
  if (confirmMessage && !confirm(confirmMessage)) {
    event.preventDefault();
    return;
  }

  // Handle AJAX forms
  if (form.hasAttribute('data-ajax')) {
    event.preventDefault();
    await handleAjaxFormSubmit(form);
  }
}

// Initialize all forms
function initForms() {
  document.querySelectorAll('form[data-validate]').forEach(setupFormValidation);
  document.addEventListener('submit', handleFormSubmit);
}

// Simple API
const FormUtils = {
  setupFormValidation,
  validateField,
  setFormLoading,
  showFormValidationErrors,
};

// Auto-initialize
if (typeof window !== 'undefined' && !window.formsInitialized) {
  window.formsInitialized = true;
  window.FormUtils = FormUtils;

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initForms);
  } else {
    initForms();
  }
}

export default FormUtils;
export { setupFormValidation, validateField, setFormLoading, showFormValidationErrors, initForms };
