/**
 * Error Pages Module
 * Handles functionality for error pages (400, 404, 500, etc.)
 */

/**
 * Initialize error page functionality
 */
function init() {
  // Use event delegation for error page actions
  document.addEventListener('click', (event) => {
    const button = event.target.closest('[data-action="back"]');
    if (button) {
      window.history.back();
    }
  });
}

// Initialize when the DOM is fully loaded
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', init);
} else {
  // DOMContentLoaded has already fired
  init();
}

// Export for testing
export { init };
