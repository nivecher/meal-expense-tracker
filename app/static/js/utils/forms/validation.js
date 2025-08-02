/**
 * Form validation utilities
 * @module FormValidation
 */

/**
 * Get validation message for a field based on its validation state
 * @param {HTMLInputElement|HTMLSelectElement|HTMLTextAreaElement} field - The field to get message for
 * @returns {string} The validation message
 */
const getValidationMessage = (field) => {
  if (field.validity.valueMissing) {
    return field.getAttribute('data-required-message') || 'This field is required';
  }
  if (field.validity.typeMismatch) {
    return field.getAttribute('data-type-message') || 'Please enter a valid value';
  }
  if (field.validity.patternMismatch) {
    return field.getAttribute('data-pattern-message') || 'Please match the requested format';
  }
  if (field.validity.tooShort || field.validity.tooLong) {
    return (
      field.getAttribute('data-length-message') ||
      `Please enter between ${field.minLength} and ${field.maxLength} characters`
    );
  }
  return field.validationMessage;
};

/**
 * Validate a single form field
 * @param {HTMLInputElement|HTMLSelectElement|HTMLTextAreaElement} field - The field to validate
 * @returns {boolean} Whether the field is valid
 */
const validateField = (field) => {
  const form = field.closest('form');
  if (!form) {
    return false;
  }

  const feedback = field.nextElementSibling;
  if (!feedback?.classList.contains('invalid-feedback')) {
    return field.checkValidity();
  }

  const isValid = field.checkValidity();
  field.classList.toggle('is-invalid', !isValid);

  if (!isValid) {
    feedback.textContent = getValidationMessage(field);
  } else {
    feedback.textContent = '';
  }

  return isValid;
};

/**
 * Show validation errors for a form
 * @param {HTMLFormElement} form - The form to show errors for
 */
const showFormValidationErrors = (form) => {
  const invalidFields = Array.from(form.querySelectorAll(':invalid'));

  invalidFields.forEach((field) => {
    const feedback = field.nextElementSibling;
    if (feedback?.classList.contains('invalid-feedback')) {
      field.classList.add('is-invalid');
      feedback.textContent = getValidationMessage(field);
    }
  });

  const [firstInvalid] = invalidFields;
  if (firstInvalid) {
    firstInvalid.focus();
    firstInvalid.scrollIntoView({
      behavior: 'smooth',
      block: 'center',
    });
  }
};

/**
 * Reset validation state for a form
 * @param {HTMLFormElement} form - The form to reset
 */
const resetFormValidation = (form) => {
  form.classList.remove('was-validated');
  form.querySelectorAll('.is-invalid').forEach((field) => {
    field.classList.remove('is-invalid');
    const feedback = field.nextElementSibling;
    if (feedback?.classList.contains('invalid-feedback')) {
      feedback.textContent = '';
    }
  });
};

export {
  getValidationMessage,
  validateField,
  showFormValidationErrors,
  resetFormValidation,
};
