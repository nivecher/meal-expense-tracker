/**
 * Robust Favicon Handler Utility
 * Handles favicon loading with multiple fallback strategies
 * Following TIGER principles: Safety, Performance, Developer Experience
 */

/**
 * Configuration for favicon sources with fallback priority
 */
const FAVICON_SOURCES = [
  {
    name: 'google',
    url: (domain) => `https://www.google.com/s2/favicons?domain=${domain}&sz=32`,
    timeout: 3000, // 3 seconds
  },
  {
    name: 'duckduckgo',
    url: (domain) => `https://icons.duckduckgo.com/ip3/${domain}.ico`,
    timeout: 3000,
  },
  {
    name: 'favicon.io',
    url: (domain) => `https://favicons.githubusercontent.com/${domain}`,
    timeout: 3000,
  },
];

/**
 * Cache for favicon results to avoid repeated requests
 */
const faviconCache = new Map();

/**
 * Extract clean domain from URL
 * @param {string} url - The website URL
 * @returns {string} - Clean domain name
 */
function extractDomain(url) {
  if (!url || typeof url !== 'string') {
    return '';
  }

  try {
    // Remove protocol and www
    let domain = url
      .replace(/^https?:\/\//, '')
      .replace(/^www\./, '')
      .split('/')[0]; // Remove path

    // Handle edge cases
    if (domain.includes('.')) {
      return domain;
    }
    return '';
  } catch (error) {
    console.warn('Error extracting domain from URL:', url, error);
    return '';
  }
}

/**
 * Try to load favicon from a specific source
 * @param {HTMLImageElement} imgElement - The image element
 * @param {string} src - The favicon URL
 * @param {number} timeout - Timeout in milliseconds
 * @returns {Promise<boolean>} - Whether the favicon loaded successfully
 */
function tryFaviconSource(imgElement, src, timeout = 3000) {
  return new Promise((resolve) => {
    const timeoutId = setTimeout(() => {
      resolve(false);
    }, timeout);

    const testImg = new Image();
    testImg.onload = () => {
      clearTimeout(timeoutId);
      resolve(true);
    };
    testImg.onerror = () => {
      clearTimeout(timeoutId);
      resolve(false);
    };
    testImg.src = src;
  });
}

/**
 * Load favicon with fallback strategy
 * @param {HTMLImageElement} imgElement - The image element to update
 * @param {string} website - The restaurant website URL
 * @param {Object} options - Configuration options
 */
export async function loadFaviconWithFallback(imgElement, website, options = {}) {
  const {
    fallbackSelector = '.restaurant-fallback-icon',
    hideImage = true,
    showFallback = true,
    size = 32,
  } = options;

  // Input validation - safety first
  if (!imgElement || !(imgElement instanceof HTMLImageElement)) {
    console.warn('Invalid image element provided to loadFaviconWithFallback');
    return;
  }

  if (!website || typeof website !== 'string') {
    console.warn('Invalid website URL provided');
    return;
  }

  const domain = extractDomain(website);
  if (!domain) {
    console.warn('Could not extract domain from website:', website);
    handleFaviconError(imgElement, { fallbackSelector, hideImage, showFallback });
    return;
  }

  // Check cache first
  const cacheKey = `${domain}-${size}`;
  if (faviconCache.has(cacheKey)) {
    const cachedResult = faviconCache.get(cacheKey);
    if (cachedResult.success) {
      imgElement.src = cachedResult.src;
      imgElement.style.opacity = '1';
      return;
    } else {
      // Cached failure - show fallback immediately
      handleFaviconError(imgElement, { fallbackSelector, hideImage, showFallback });
      return;
    }
  }

  try {
    // Try each favicon source in order
    let success = false;
    let workingSrc = '';

    for (const source of FAVICON_SOURCES) {
      try {
        const src = source.url(domain);
        const loaded = await tryFaviconSource(imgElement, src, source.timeout);

        if (loaded) {
          workingSrc = src;
          success = true;
          break;
        }
      } catch (error) {
        console.warn(`Favicon source ${source.name} failed for ${domain}:`, error);
      }
    }

    // Cache the result
    faviconCache.set(cacheKey, { success, src: workingSrc });

    if (success && workingSrc) {
      imgElement.src = workingSrc;
      imgElement.style.opacity = '1';
    } else {
      handleFaviconError(imgElement, { fallbackSelector, hideImage, showFallback });
    }

  } catch (error) {
    console.error('Error loading favicon with fallback:', error);
    handleFaviconError(imgElement, { fallbackSelector, hideImage, showFallback });
  }
}

/**
 * Handle favicon loading errors by showing fallback icon
 * @param {HTMLImageElement} imgElement - The failed image element
 * @param {Object} options - Configuration options
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
 * Initialize robust favicon handling for all restaurant favicons on the page
 * @param {string} selector - CSS selector for favicon containers
 */
export function initializeRobustFaviconHandling(selector = '.restaurant-favicon') {
  // Input validation
  if (!selector || typeof selector !== 'string') {
    console.warn('Invalid selector provided to initializeRobustFaviconHandling');
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
        const website = favicon.dataset.website;
        if (website) {
          // Use robust loading with fallback
          loadFaviconWithFallback(favicon, website, {
            size: favicon.dataset.size || 32,
          });
        } else {
          // Fallback to simple error handling if no website data
          if (!favicon.onerror) {
            favicon.onerror = () => handleFaviconError(favicon);
          }
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
    console.error('Error initializing robust favicon handling:', error);
  }
}

/**
 * Clear favicon cache (useful for testing or memory management)
 */
export function clearFaviconCache() {
  faviconCache.clear();
}

/**
 * Get favicon cache statistics
 */
export function getFaviconCacheStats() {
  return {
    size: faviconCache.size,
    keys: Array.from(faviconCache.keys()),
  };
}

// Auto-initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
  initializeRobustFaviconHandling('.restaurant-favicon');
  initializeRobustFaviconHandling('.restaurant-favicon-table');
});

// Export for global access
window.RobustFaviconHandler = {
  loadWithFallback: loadFaviconWithFallback,
  handleError: handleFaviconError,
  handleLoad: handleFaviconLoad,
  initialize: initializeRobustFaviconHandling,
  clearCache: clearFaviconCache,
  getCacheStats: getFaviconCacheStats,
};
