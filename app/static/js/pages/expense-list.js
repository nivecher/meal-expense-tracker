/**
 * Expenses List Page JavaScript
 * Handles date validation and form submission for the expenses list page.
 */

document.addEventListener('DOMContentLoaded', () => {
  const form = document.querySelector('form[method="get"]');
  if (!form) return;

  // Initialize date inputs
  const startDateInput = document.getElementById('start_date');
  const endDateInput = document.getElementById('end_date');
  const searchInput = document.getElementById('search');

  // Validate date range when form is submitted
  form.addEventListener('submit', (e) => {
    // Clear any existing validation messages
    clearValidationErrors();

    // Get date values
    const startDate = startDateInput.value ? new Date(startDateInput.value) : null;
    const endDate = endDateInput.value ? new Date(endDateInput.value) : null;

    // Validate dates
    let isValid = true;

    // Check if start date is valid
    if (startDateInput.value && isNaN(startDate.getTime())) {
      showError(startDateInput, 'Please enter a valid start date');
      isValid = false;
    }

    // Check if end date is valid
    if (endDateInput.value && isNaN(endDate.getTime())) {
      showError(endDateInput, 'Please enter a valid end date');
      isValid = false;
    }

    // Check if start date is before end date
    if (startDate && endDate && startDate > endDate) {
      showError(startDateInput, 'Start date must be before end date');
      showError(endDateInput, 'End date must be after start date');
      isValid = false;
    }

    // If validation fails, prevent form submission
    if (!isValid) {
      e.preventDefault();
      // Focus on the first invalid field
      const firstInvalid = form.querySelector('.is-invalid');
      if (firstInvalid) {
        firstInvalid.focus();
      }
    }
  });

  // Clear validation errors when user starts typing or changes dates
  if (startDateInput) {
    startDateInput.addEventListener('input', clearValidationErrors);
  }
  if (endDateInput) {
    endDateInput.addEventListener('input', clearValidationErrors);
  }
  if (searchInput) {
    searchInput.addEventListener('input', clearValidationErrors);
  }

  /**
     * Show an error message for a form field
     * @param {HTMLElement} input - The input element to show the error for
     * @param {string} message - The error message to display
     */
  function showError(input, message) {
    // Add error class to input
    input.classList.add('is-invalid');

    // Create or update error message
    let errorElement = input.nextElementSibling;
    if (!errorElement || !errorElement.classList.contains('invalid-feedback')) {
      errorElement = document.createElement('div');
      errorElement.className = 'invalid-feedback';
      input.parentNode.insertBefore(errorElement, input.nextSibling);
    }
    errorElement.textContent = message;
  }

  /**
     * Clear all validation errors from the form
     */
  function clearValidationErrors() {
    // Remove error classes
    const invalidInputs = form.querySelectorAll('.is-invalid');
    invalidInputs.forEach((input) => {
      input.classList.remove('is-invalid');
    });

    // Remove error messages
    const errorMessages = form.querySelectorAll('.invalid-feedback');
    errorMessages.forEach((message) => {
      message.remove();
    });
  }
});
