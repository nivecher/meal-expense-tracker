/**
 * Form submission utilities
 * @module FormSubmission
 */

import { resetFormValidation } from './validation.js';
import { apiRequest } from '../api-utils.js';

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
/**
 * Get the CSRF token from the meta tag
 * @returns {string} The CSRF token
 */
/**
 * Handle AJAX form submission
 * @param {HTMLFormElement} form - The form being submitted
 * @returns {Promise<void>}
 */
const handleAjaxFormSubmit = async(form) => {
  const formData = new FormData(form);
  const method = (form.getAttribute('method') || 'POST').toUpperCase();
  const url = form.getAttribute('action') || window.location.pathname;

  try {
    setFormLoading(form, true);

    // Convert FormData to plain object for JSON requests
    let body = formData;
    const contentType = form.getAttribute('enctype') || form.enctype;

    if (contentType === 'application/json' || !(body instanceof FormData)) {
      const data = {};
      formData.forEach((value, key) => {
        data[key] = value;
      });
      body = data;
    }

    // Use our API utility to handle the request
    const result = await apiRequest(url, {
      method,
      body: method === 'GET' ? undefined : body,
      params: method === 'GET' ? Object.fromEntries(formData.entries()) : undefined,
      headers: {
        Accept: 'application/json',
      },
    });

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
