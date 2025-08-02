/**
 * Form submission utilities
 * @module FormSubmission
 */

import { resetFormValidation } from './validation.js';

/**
 * Set loading state for a form
 * @param {HTMLFormElement} form - The form to update
 * @param {boolean} isLoading - Whether the form is loading
 */
const setFormLoading = (form, isLoading) => {
  const submitButton = form.querySelector('button[type="submit"]');
  if (!submitButton) {
    return;
  }

  const inputs = form.querySelectorAll('input, select, textarea, button');
  inputs.forEach((input) => {
    input.disabled = isLoading;
  });

  const originalText = submitButton.textContent;
  if (isLoading) {
    submitButton.dataset.originalText = originalText;
    submitButton.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Loading...';
  } else {
    submitButton.textContent = submitButton.dataset.originalText || originalText;
  }

  form.classList.toggle('is-submitting', isLoading);
};

/**
 * Handle form submission errors
 * @param {Error} error - The error that occurred
 */
const handleFormSubmissionError = (error) => {
  console.error('Form submission error:', error);
  const errorMessage = error.message || 'An error occurred while submitting the form. Please try again.';

  if (window.showToast) {
    window.showToast.error(errorMessage);
  } else {
    alert(errorMessage);
  }
};

/**
 * Handle form submission response
 * @param {Object} result - The parsed JSON response
 * @param {HTMLFormElement} form - The form being submitted
 */
const handleFormSubmissionResponse = (result, form) => {
  if (result.redirect) {
    const redirectUrl = result.redirect;
    window.setTimeout(() => {
      window.location.href = redirectUrl;
    }, 0);
    return;
  }

  if (result.message) {
    if (window.showToast) {
      window.showToast.success(result.message);
    } else {
      window.alert(result.message);
    }
  }

  if (result.success) {
    form.reset();
    resetFormValidation(form);
  }
};

/**
 * Handle AJAX form submission
 * @param {HTMLFormElement} form - The form being submitted
 * @returns {Promise<void>}
 */
const handleAjaxFormSubmit = async (form) => {
  const requestOptions = {
    method: form.getAttribute('method') || 'POST',
    body: new FormData(form),
    headers: { 'X-Requested-With': 'XMLHttpRequest' },
  };

  try {
    setFormLoading(form, true);
    const response = await fetch(
      form.getAttribute('action') || window.location.href,
      requestOptions,
    );

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const result = await response.json();
    handleFormSubmissionResponse(result, form);
  } catch (error) {
    handleFormSubmissionError(error);
  } finally {
    setFormLoading(form, false);
  }
};

export {
  handleFormSubmissionError,
  handleFormSubmissionResponse,
  handleAjaxFormSubmit,
  setFormLoading,
};
