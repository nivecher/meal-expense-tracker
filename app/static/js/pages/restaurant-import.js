/**
 * Restaurant Import Page
 *
 * Handles form validation for restaurant CSV import functionality.
 * This replaces the inline JavaScript in the restaurants/import.html template.
 */

document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('import-form');
  const fileInput = form.querySelector('#file');

  // Reset any initial validation states
  fileInput.classList.remove('is-invalid', 'is-valid');

  form.addEventListener('submit', (event) => {
    // Clear any previous validation states
    fileInput.classList.remove('is-invalid', 'is-valid');

    if (!fileInput.files.length) {
      event.preventDefault();
      event.stopPropagation();
      fileInput.classList.add('is-invalid');
      form.classList.add('was-validated');
    } else {
      // File is selected, allow form submission
      fileInput.classList.add('is-valid');
    }
  });

  fileInput.addEventListener('change', function() {
    // Clear any validation classes when file selection changes
    this.classList.remove('is-invalid', 'is-valid');

    if (this.files.length) {
      // File selected, show positive feedback but don't persist it
      this.classList.add('is-valid');

      // Remove validation state after a short delay to prevent persistent green border
      setTimeout(() => {
        if (!form.classList.contains('was-validated')) {
          this.classList.remove('is-valid');
        }
      }, 1000);
    }
  });

  // Clear validation states when form is reset or page loads
  form.addEventListener('reset', () => {
    fileInput.classList.remove('is-invalid', 'is-valid');
    form.classList.remove('was-validated');
  });
});
