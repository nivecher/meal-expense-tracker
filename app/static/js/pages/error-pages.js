/**
 * Error Pages Module
 * Handles functionality for error pages (400, 404, 500, etc.)
 */

/**
 * Initialize error page functionality
 */
function initErrorPage() {
    // Add click handler for back button
    const backButton = document.querySelector('.btn-error-back');
    if (backButton) {
        backButton.addEventListener('click', () => {
            window.history.back();
        });
    }
}

// Initialize when the DOM is fully loaded
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initErrorPage);
} else {
    // DOMContentLoaded has already fired
    initErrorPage();
}

// Export for testing
export { initErrorPage };
