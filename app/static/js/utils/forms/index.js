/**
 * Main forms module that combines all form utilities
 * @module FormUtils
 */

import { validateField, showFormValidationErrors, resetFormValidation } from './validation.js';
import { handleAjaxFormSubmit, setFormLoading } from './submission.js';

/**
 * Set up real-time validation for form inputs
 * @param {HTMLFormElement} form - The form to set up validation for
 */
const setupRealTimeValidation = (form) => {
  form.querySelectorAll('input, select, textarea').forEach((input) => {
    input.addEventListener('input', () => validateField(input));
  });
};

/**
 * Handle form validation on submit
 * @param {Event} event - The form submit event
 */
const handleFormValidation = (event) => {
  const form = event.target;
  if (!form.checkValidity()) {
    event.preventDefault();
    event.stopPropagation();
    showFormValidationErrors(form);
  }
  form.classList.add('was-validated');
};

/**
 * Set up form validation
 * @param {HTMLFormElement} form - The form to set up
 */
const setupFormValidation = (form) => {
  form.setAttribute('novalidate', '');
  form.addEventListener('submit', handleFormValidation, false);
  setupRealTimeValidation(form);
};

/**
 * Handle form submission
 * @param {Event} event - The form submit event
 * @returns {Promise<void>}
 */
const handleFormSubmit = async(event) => {
  const form = event.target.closest('form');
  if (!form) {
    return;
  }

  if (form.classList.contains('is-submitting')) {
    event.preventDefault();
    return;
  }

  const confirmMessage = form.getAttribute('data-confirm');
  if (confirmMessage && !window.confirm(confirmMessage)) {
    event.preventDefault();
    return;
  }

  if (!form.hasAttribute('data-ajax')) {
    if (form.classList.contains('is-submitting')) {
      event.preventDefault();
    }
    return;
  }

  event.preventDefault();
  await handleAjaxFormSubmit(form);
};

/**
 * Initialize all forms with data-validate attribute
 */
const initForms = () => {
  const forms = document.querySelectorAll('form[data-validate]');
  forms.forEach((form) => setupFormValidation(form));
  document.addEventListener('submit', handleFormSubmit);
};

// Public API
const FormUtils = {
  setupFormValidation,
  validateField,
  resetFormValidation,
  setFormLoading,
  showFormValidationErrors,
  resetFormLoading: (form) => {
    console.warn('FormUtils.resetFormLoading is deprecated. Use setFormLoading(form, false) instead.');
    setFormLoading(form, false);
  },
};

// Initialize when the DOM is ready
const initialize = () => {
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initForms);
  } else {
    initForms();
  }
};

// Auto-initialize if not in a module context
if (typeof window !== 'undefined' && !window.formsInitialized) {
  window.formsInitialized = true;
  window.FormUtils = FormUtils;
  initialize();
}

export default FormUtils;
export {
  setupFormValidation,
  validateField,
  resetFormValidation,
  setFormLoading,
  showFormValidationErrors,
  initForms,
  initialize,
};
