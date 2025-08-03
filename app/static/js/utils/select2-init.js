/**
 * Select2 Initialization Module
 * Handles initialization of Select2 components
 */

/**
 * Initialize all Select2 elements on the page
 */
function initSelect2() {
  if (window.jQuery && window.jQuery.fn.select2) {
    $('select.select2').select2({
      theme: 'bootstrap-5',
      width: '100%',
      dropdownAutoWidth: true,
      dropdownParent: $('select.select2').parent(),
    });
  }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', initSelect2);

// Export for testing
export { initSelect2 };
