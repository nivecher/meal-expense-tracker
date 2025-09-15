/**
 * Simple Favicon Handler Utility
 * CSP-compliant favicon error handling without external API calls
 * Following TIGER principles: Safety, Performance, Developer Experience
 */

/**
 * Handle favicon loading errors by showing fallback icon
 *
 * @param {HTMLImageElement} imgElement - The failed image element
 * @param {Object} options - Configuration options
 * @param {string} options.fallbackSelector - CSS selector for fallback icon (default: '.restaurant-fallback-icon')
 * @param {boolean} options.hideImage - Whether to hide the failed image (default: true)
 * @param {boolean} options.showFallback - Whether to show the fallback icon (default: true)
 */
export function handleFaviconError(imgElement, options = {}) {
  const {
    fallbackSelector = '.restaurant-fallback-icon',
    hideImage = true,
    showFallback = true,
  } = options;

  // Input validation - safety first
  if (!imgElement || !(imgElement instanceof HTMLImageElement)) {
    console.warn('Invalid image element provided to handleFaviconError');
    return;
  }

  try {
    // Hide the failed image
    if (hideImage) {
      imgElement.style.display = 'none';
    }

    // Find and show the fallback icon
    if (showFallback) {
      const container = imgElement.parentElement;
      if (container) {
        const fallbackIcon = container.querySelector(fallbackSelector);
        if (fallbackIcon) {
          fallbackIcon.style.display = 'inline-block';
          fallbackIcon.classList.remove('d-none');
        } else {
          // Try alternative selectors for different layouts
          const alternativeSelectors = [
            '.restaurant-fallback-icon-table',
            '.restaurant-fallback-icon',
            '.restaurant-fallback-icon-large',
            'i.fa-utensils',
          ];

          for (const selector of alternativeSelectors) {
            const altIcon = container.querySelector(selector);
            if (altIcon) {
              altIcon.style.display = 'inline-block';
              altIcon.classList.remove('d-none');
              break;
            }
          }
        }
      }
    }

  } catch (error) {
    console.error('Error handling favicon fallback:', error);
  }
}

/**
 * Handle successful favicon loads
 *
 * @param {HTMLImageElement} imgElement - The successfully loaded image element
 */
export function handleFaviconLoad(imgElement) {
  // Input validation
  if (!imgElement || !(imgElement instanceof HTMLImageElement)) {
    return;
  }

  try {
    // Show the image with smooth transition
    imgElement.style.opacity = '1';
  } catch (error) {
    console.error('Error handling favicon load:', error);
  }
}

/**
 * Initialize favicon handling for all restaurant favicons on the page
 *
 * @param {string} selector - CSS selector for favicon containers (default: '.restaurant-favicon')
 */
export function initializeFaviconHandling(selector = '.restaurant-favicon') {
  // Input validation
  if (!selector || typeof selector !== 'string') {
    console.warn('Invalid selector provided to initializeFaviconHandling');
    return;
  }

  try {
    const favicons = document.querySelectorAll(selector);

    // Enforce bounds to prevent excessive processing
    if (favicons.length > 1000) {
      console.warn('Too many favicons found, limiting to first 1000');
    }

    const faviconsToProcess = Array.from(favicons).slice(0, 1000);

    faviconsToProcess.forEach((favicon, index) => {
      try {
        // Ensure error handler is attached
        if (!favicon.onerror) {
          favicon.onerror = () => handleFaviconError(favicon);
        }

        // Ensure load handler is attached
        if (!favicon.onload) {
          favicon.onload = () => handleFaviconLoad(favicon);
        }
      } catch (error) {
        console.error(`Error initializing favicon ${index}:`, error);
      }
    });

  } catch (error) {
    console.error('Error initializing favicon handling:', error);
  }
}

// Auto-initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
  initializeFaviconHandling('.restaurant-favicon');
  initializeFaviconHandling('.restaurant-favicon-table');
});

// Export for global access
window.FaviconHandler = {
  handleError: handleFaviconError,
  handleLoad: handleFaviconLoad,
  initialize: initializeFaviconHandling,
};
