/**
 * Restaurant Import Page JavaScript
 * Handles form validation and file upload for importing restaurants
 */

document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('import-form');
    const fileInput = document.getElementById('file');
    const maxFileSize = 5 * 1024 * 1024; // 5MB in bytes

    if (!form) return;

    // Client-side validation
    form.addEventListener('submit', (e) => {
        if (!validateFile()) {
            e.preventDefault();
        }
    });

    // Validate file on change
    if (fileInput) {
        fileInput.addEventListener('change', validateFile);
    }

    /**
     * Validate the selected file
     * @returns {boolean} True if file is valid, false otherwise
     */
    function validateFile() {
        if (!fileInput.files.length) {
            showError('Please select a file to upload');
            return false;
        }

        const file = fileInput.files[0];
        const fileExt = file.name.split('.').pop().toLowerCase();

        // Check file extension
        if (!['csv', 'json'].includes(fileExt)) {
            showError('Please upload a CSV or JSON file');
            return false;
        }

        // Check file size
        if (file.size > maxFileSize) {
            showError('File size exceeds 5MB limit');
            return false;
        }

        // Clear any previous errors
        clearError();
        return true;
    }

    /**
     * Display an error message
     * @param {string} message - The error message to display
     */
    function showError(message) {
        clearError();

        const errorDiv = document.createElement('div');
        errorDiv.className = 'invalid-feedback d-block';
        errorDiv.textContent = message;

        fileInput.classList.add('is-invalid');
        fileInput.after(errorDiv);
    }

    /**
     * Clear any displayed error messages
     */
    function clearError() {
        const existingError = fileInput.nextElementSibling;
        if (existingError && existingError.classList.contains('invalid-feedback')) {
            existingError.remove();
        }
        fileInput.classList.remove('is-invalid');
    }
});
