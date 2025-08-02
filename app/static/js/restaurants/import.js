/**
 * Client-side validation and functionality for the restaurant import page.
 */

document.addEventListener('DOMContentLoaded', () => {
  initializeImportForm();
});

/**
 * Initialize the import form with event listeners and validation.
 */
function initializeImportForm () {
  const form = document.querySelector('form.needs-validation');
  if (!form) return;

  const fileInput = form.querySelector('input[type="file"]');
  const submitButton = form.querySelector('button[type="submit"]');

  if (fileInput) {
    fileInput.addEventListener('change', handleFileSelect);
  }

  form.addEventListener('submit', handleFormSubmit);
}

/**
 * Handle file selection and update UI with selected file name.
 * @param {Event} event - The file input change event
 */
function handleFileSelect (event) {
  const fileInput = event.target;
  const fileNameDisplay = document.getElementById('file-name');

  if (fileInput.files.length > 0) {
    const fileName = fileInput.files[0].name;
    if (fileNameDisplay) {
      fileNameDisplay.textContent = fileName;
    }
  } else {
    if (fileNameDisplay) {
      fileNameDisplay.textContent = 'No file chosen';
    }
  }
}

/**
 * Handle form submission with custom validation.
 * @param {Event} event - The form submit event
 */
function handleFormSubmit (event) {
  const form = event.target;
  const fileInput = form.querySelector('input[type="file"]');
  const MAX_FILE_SIZE = 5 * 1024 * 1024; // 5MB in bytes

  // Reset previous validation
  form.classList.remove('was-validated');

  // Check if file is selected
  if (fileInput.files.length === 0) {
    event.preventDefault();
    event.stopPropagation();
    fileInput.setCustomValidity('Please select a file to upload.');
    form.classList.add('was-validated');
    return;
  }

  // Check file type
  const file = fileInput.files[0];
  if (!file.name.toLowerCase().endsWith('.csv')) {
    event.preventDefault();
    event.stopPropagation();
    fileInput.setCustomValidity('Only CSV files are allowed.');
    form.classList.add('was-validated');
    return;
  }

  // Check file size
  if (file.size > MAX_FILE_SIZE) {
    event.preventDefault();
    event.stopPropagation();
    fileInput.setCustomValidity('File size must be less than 5MB.');
    form.classList.add('was-validated');
    return;
  }

  // If we get here, validation passed
  fileInput.setCustomValidity('');

  // Show loading state
  const submitButton = form.querySelector('button[type="submit"]');
  if (submitButton) {
    submitButton.disabled = true;
    submitButton.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>Importing...';
  }
}

// Export functions for testing
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    initializeImportForm,
    handleFileSelect,
    handleFormSubmit,
  };
}
