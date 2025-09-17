/**
 * Robust Favicon Handler Utility
 * Handles favicon loading with multiple fallback strategies
 * Following TIGER principles: Safety, Performance, Developer Experience
 *
 * Version: 3.1.0 - Fixed Root Domain Detection for Subdomains
 * Last Updated: 2024-01-XX
 */

/**
 * Configuration for favicon sources with fallback priority
 */
const FAVICON_SOURCES = [
  {
    name: 'google_legacy',
    url: (domain) => `https://www.google.com/s2/favicons?domain=${domain}&sz=32`,
    timeout: 3000,
    quality: 'high', // Most reliable and widely supported
  },
  {
    name: 'favicon.io',
    url: (domain) => `https://favicons.githubusercontent.com/${domain}`,
    timeout: 3000,
    quality: 'medium', // GitHub-hosted favicons, good coverage
  },
  {
    name: 'clearbit',
    url: (domain) => `https://logo.clearbit.com/${domain}`,
    timeout: 3000,
    quality: 'medium', // Good quality but less reliable coverage
  },
];

/**
 * Cache for favicon results to avoid repeated requests
 * Uses Map instead of localStorage to avoid tracking prevention issues
 */
const faviconCache = new Map();

// Cache for domains that consistently fail favicon requests
const failedDomainsCache = new Map();

// Known problematic domains that should skip favicon requests
const problematicDomains = new Set([
  'square.site', // Square sites often have favicon issues
  'wix.com',
  'squarespace.com',
  'weebly.com'
]);

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
    const domain = url
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
 * Extract root domain from subdomain
 * @param {string} domain - The full domain
 * @returns {string} - The root domain
 */
function extractRootDomain(domain) {
  if (!domain || typeof domain !== 'string') {
    return domain;
  }

  // Split by dots and get the last two parts for most domains
  const parts = domain.split('.');
  if (parts.length >= 2) {
    // For domains like example.co.uk, we need the last 2 parts
    // For domains like subdomain.example.com, we need the last 2 parts
    return parts.slice(-2).join('.');
  }

  return domain;
}

/**
 * Check if domain should skip favicon requests
 * @param {string} domain - The domain to check
 * @returns {boolean} - Whether to skip favicon requests
 */
function shouldSkipFaviconRequest(domain) {
  // Check if domain is in problematic domains list
  if (problematicDomains.has(domain)) {
    console.log(`Domain "${domain}" found in problematic domains list`);
    return true;
  }

  // Check if root domain is in problematic domains list
  const rootDomain = extractRootDomain(domain);
  if (problematicDomains.has(rootDomain)) {
    console.log(`Root domain "${rootDomain}" found in problematic domains list for "${domain}"`);
    return true;
  }

  // Check if domain has consistently failed favicon requests
  const failedCount = failedDomainsCache.get(domain) || 0;
  if (failedCount >= 3) {
    console.log(`Domain "${domain}" has failed ${failedCount} times, skipping`);
    return true;
  }

  console.log(`Domain "${domain}" (root: "${rootDomain}") is not problematic, proceeding with favicon request`);
  return false;
}

/**
 * Mark domain as failed for favicon requests
 * @param {string} domain - The domain that failed
 */
function markDomainAsFailed(domain) {
  const currentCount = failedDomainsCache.get(domain) || 0;
  failedDomainsCache.set(domain, currentCount + 1);
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
    // Input validation - safety first
    if (!src || typeof src !== 'string') {
      resolve(false);
      return;
    }

    const timeoutId = setTimeout(() => {
      resolve(false);
    }, timeout);

    // Create a hidden image element to test the favicon
    const testImg = document.createElement('img');
    testImg.style.display = 'none';
    testImg.style.position = 'absolute';
    testImg.style.left = '-9999px';
    testImg.style.top = '-9999px';
    document.body.appendChild(testImg);

    testImg.onload = () => {
      clearTimeout(timeoutId);
      document.body.removeChild(testImg);
      resolve(true);
    };

    testImg.onerror = () => {
      clearTimeout(timeoutId);
      document.body.removeChild(testImg);
      // All favicon service errors are expected, don't log them
      resolve(false);
    };

    // Set the source to trigger the load
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

  // Smart skip: Check if domain should skip favicon requests
  console.log(`Extracted domain: "${domain}" from URL: "${website}"`);
  if (shouldSkipFaviconRequest(domain)) {
    console.log(`Skipping favicon request for problematic domain: ${domain}`);
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
    }
    // Cached failure - show fallback immediately
    handleFaviconError(imgElement, { fallbackSelector, hideImage, showFallback });
    return;

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
      // Mark domain as failed for future requests
      markDomainAsFailed(domain);
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
        const { website } = favicon.dataset;
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
 * Clear failed domains cache
 */
export function clearFailedDomainsCache() {
  failedDomainsCache.clear();
}

/**
 * Get failed domains cache stats
 * @returns {Object} - Cache statistics
 */
export function getFailedDomainsCacheStats() {
  return {
    size: failedDomainsCache.size,
    domains: Array.from(failedDomainsCache.entries())
  };
}

/**
 * Debug function to test favicon sources for a specific domain
 * @param {string} domain - The domain to test
 * @returns {Promise<Object>} - Results of testing all favicon sources
 */
export async function debugFaviconSources(domain) {
  if (!domain || typeof domain !== 'string') {
    return { error: 'Invalid domain provided' };
  }

  const results = {
    domain,
    sources: [],
    workingSources: [],
    failedSources: []
  };

  for (const source of FAVICON_SOURCES) {
    const url = source.url(domain);
    const startTime = Date.now();

    try {
      const success = await tryFaviconSource(null, url, source.timeout);
      const duration = Date.now() - startTime;

      const result = {
        name: source.name,
        url,
        success,
        duration,
        timeout: source.timeout
      };

      results.sources.push(result);

      if (success) {
        results.workingSources.push(result);
      } else {
        results.failedSources.push(result);
      }
    } catch (error) {
      results.sources.push({
        name: source.name,
        url,
        success: false,
        error: error.message,
        duration: Date.now() - startTime
      });
      results.failedSources.push(source.name);
    }
  }

  return results;
}

/**
 * Get favicon cache statistics
 * @returns {Object} - Cache statistics
 */
export function getFaviconCacheStats() {
  const stats = {
    totalEntries: faviconCache.size,
    successfulEntries: 0,
    failedEntries: 0,
    entries: []
  };

  for (const [key, value] of faviconCache.entries()) {
    if (value.success) {
      stats.successfulEntries++;
    } else {
      stats.failedEntries++;
    }

    stats.entries.push({
      key,
      success: value.success,
      src: value.src
    });
  }

  return stats;
}

/**
 * Suppress CORS errors for favicon requests globally
 * This prevents console spam from expected CORS failures
 */
function suppressFaviconCORSErrors() {
  // Override the global error handler to catch CORS errors
  window.addEventListener('error', function(event) {
    if (event.message && event.message.includes('CORS') &&
        (event.filename && event.filename.includes('favicon.ico'))) {
      event.preventDefault(); // Prevent the error from being logged
      return false;
    }
  }, true);

  // Add a more aggressive error listener for network errors
  window.addEventListener('error', function(event) {
    if (event.target && event.target.tagName === 'IMG' &&
        event.target.src && (
          event.target.src.includes('t1.gstatic.com/faviconV2') ||
          event.target.src.includes('t2.gstatic.com/faviconV2') ||
          event.target.src.includes('favicon.ico') ||
          event.target.src.includes('google.com/s2/favicons') ||
          event.target.src.includes('favicons.githubusercontent.com') ||
          event.target.src.includes('logo.clearbit.com')
        )) {
      event.preventDefault();
      event.stopPropagation();
      return false;
    }
  }, true);

  // Override the browser's native error logging for network requests
  const originalError = window.onerror;
  window.onerror = function(message, source, lineno, colno, error) {
    if (message && (
        message.includes('t1.gstatic.com/faviconV2') ||
        message.includes('t2.gstatic.com/faviconV2') ||
        message.includes('favicon.ico') ||
        message.includes('CORS') ||
        message.includes('404 (Not Found)')
    )) {
      return true; // Suppress the error
    }
    if (originalError) {
      return originalError.apply(this, arguments);
    }
    return false;
  };

  // Override the browser's native error logging for network requests
  const originalUnhandledRejection = window.onunhandledrejection;
  window.onunhandledrejection = function(event) {
    if (event.reason && event.reason.message && (
        event.reason.message.includes('t1.gstatic.com/faviconV2') ||
        event.reason.message.includes('t2.gstatic.com/faviconV2') ||
        event.reason.message.includes('favicon.ico') ||
        event.reason.message.includes('404')
    )) {
      event.preventDefault();
      return false;
    }
    if (originalUnhandledRejection) {
      return originalUnhandledRejection.apply(this, arguments);
    }
    return false;
  };

  // Override console methods to filter CORS favicon errors
  const originalConsoleError = console.error;
  const originalConsoleWarn = console.warn;
  const originalConsoleLog = console.log;

  console.error = function(...args) {
    const message = args.join(' ');
    // Suppress CORS errors for favicon requests
    if ((message.includes('favicon.ico') && message.includes('CORS')) ||
        (message.includes('Access to image') && message.includes('favicon.ico')) ||
        (message.includes('favicon.ico') && message.includes('ERR_FAILED')) ||
        (message.includes('favicon.ico') && message.includes('404')) ||
        (message.includes('google.com/s2/favicons') && message.includes('404')) ||
        (message.includes('t1.gstatic.com/faviconV2') && message.includes('404')) ||
        (message.includes('t2.gstatic.com/faviconV2') && message.includes('404')) ||
        (message.includes('favicons.githubusercontent.com') && message.includes('404')) ||
        (message.includes('logo.clearbit.com') && message.includes('404'))) {
      return; // Don't log favicon errors
    }
    originalConsoleError.apply(console, args);
  };

  console.warn = function(...args) {
    const message = args.join(' ');
    // Suppress CORS warnings for favicon requests
    if ((message.includes('favicon.ico') && message.includes('CORS')) ||
        (message.includes('Access to image') && message.includes('favicon.ico')) ||
        (message.includes('favicon.ico') && message.includes('ERR_FAILED')) ||
        (message.includes('favicon.ico') && message.includes('404')) ||
        (message.includes('google.com/s2/favicons') && message.includes('404')) ||
        (message.includes('t1.gstatic.com/faviconV2') && message.includes('404')) ||
        (message.includes('t2.gstatic.com/faviconV2') && message.includes('404')) ||
        (message.includes('favicons.githubusercontent.com') && message.includes('404')) ||
        (message.includes('logo.clearbit.com') && message.includes('404'))) {
      return; // Don't log favicon warnings
    }
    originalConsoleWarn.apply(console, args);
  };

  console.log = function(...args) {
    const message = args.join(' ');
    // Suppress network errors for favicon requests
    if ((message.includes('favicon.ico') && message.includes('ERR_FAILED')) ||
        (message.includes('favicon.ico') && message.includes('404')) ||
        (message.includes('favicon.ico') && message.includes('CORS')) ||
        (message.includes('google.com/s2/favicons') && message.includes('404')) ||
        (message.includes('t1.gstatic.com/faviconV2') && message.includes('404')) ||
        (message.includes('t2.gstatic.com/faviconV2') && message.includes('404')) ||
        (message.includes('favicons.githubusercontent.com') && message.includes('404')) ||
        (message.includes('logo.clearbit.com') && message.includes('404'))) {
      return; // Don't log favicon network errors
    }
    originalConsoleLog.apply(console, args);
  };

  // Override the browser's native error logging for network requests
  const originalFetch = window.fetch;
  if (originalFetch) {
    window.fetch = function(...args) {
      const url = args[0];
      if (typeof url === 'string' && (
          url.includes('google.com/s2/favicons') ||
          url.includes('t1.gstatic.com/faviconV2') ||
          url.includes('t2.gstatic.com/faviconV2') ||
          url.includes('favicons.githubusercontent.com') ||
          url.includes('logo.clearbit.com') ||
          url.includes('favicon.ico')
      )) {
        // Suppress network errors for favicon requests
        return originalFetch.apply(this, args).catch(error => {
          // Don't log favicon fetch errors
          return Promise.reject(error);
        });
      }
      return originalFetch.apply(this, args);
    };
  }

  // Override XMLHttpRequest to suppress favicon errors
  const originalXHROpen = XMLHttpRequest.prototype.open;
  XMLHttpRequest.prototype.open = function(method, url, ...args) {
    if (typeof url === 'string' && (
        url.includes('t1.gstatic.com/faviconV2') ||
        url.includes('t2.gstatic.com/faviconV2') ||
        url.includes('google.com/s2/favicons') ||
        url.includes('favicons.githubusercontent.com') ||
        url.includes('logo.clearbit.com') ||
        url.includes('favicon.ico')
    )) {
      // Suppress errors for favicon requests
      this.addEventListener('error', function(event) {
        event.preventDefault();
        event.stopPropagation();
      });
    }
    return originalXHROpen.apply(this, [method, url, ...args]);
  };
}

// Auto-initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
  // Suppress CORS errors for favicon requests
  suppressFaviconCORSErrors();

  // Clear any existing favicon cache to prevent stale data
  clearFaviconCache();

  // Log version for debugging
  console.log('Robust Favicon Handler v3.1.0 loaded - Fixed Root Domain Detection for Subdomains');

  // Initialize favicon handling
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
  clearFailedDomainsCache: clearFailedDomainsCache,
  getCacheStats: getFaviconCacheStats,
  getFailedDomainsCacheStats: getFailedDomainsCacheStats,
};
