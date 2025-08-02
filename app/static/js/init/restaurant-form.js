/**
 * Restaurant Form Initialization
 * Handles the initialization of the restaurant form page
 */

// Initialize the restaurant form when the DOM is fully loaded
document.addEventListener('DOMContentLoaded', async () => {
  try {
    // Import and initialize the restaurant form module
    const module = await import('/static/js/pages/restaurant-form.js');
    if (module && typeof module.init === 'function') {
      await module.init();
    } else {
      throw new Error('Restaurant form module not properly exported');
    }
  } catch (error) {
    console.error('Error initializing restaurant form:', error);
    showError('Failed to initialize the form. Please refresh the page and try again.');
  }

  // Initialize Select2 for any select elements
  if (window.jQuery && jQuery.fn.select2) {
    jQuery('select').select2({
      theme: 'bootstrap-5',
      width: '100%',
      placeholder: 'Select an option',
      allowClear: true,
    });
  }
});

/**
 * Show an error message to the user
 * @param {string} message - The error message to display
 */
function showError (message) {
  const errorContainer = document.getElementById('error-container');
  if (errorContainer) {
    errorContainer.textContent = message;
    errorContainer.classList.remove('d-none');
  }
}
