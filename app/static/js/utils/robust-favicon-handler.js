/**
 * Robust Favicon Handler Utility
 * Handles favicon loading with multiple fallback strategies
 * Following TIGER principles: Safety, Performance, Developer Experience
 *
 * Version: 3.6.0 - Modern Google Favicon V2 API & Enhanced Stability
 * Last Updated: 2024-01-XX
 */

/**
 * Configuration for favicon sources with seamless fallback
 * Google-style approach: try best quality first, fall back silently
 */
const FAVICON_SOURCES = [
  {
    name: 'google-favicon-v2',
    url: (domain) => `https://t3.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL&url=https://${domain}&size=64`,
    timeout: 2500,
    quality: 'high', // Best quality when available
  },
  {
    name: 'duckduckgo',
    url: (domain) => `https://icons.duckduckgo.com/ip3/${domain}.ico`,
    timeout: 2500,
    quality: 'high', // Reliable fallback
  },
];

/**
 * Cache for favicon results to avoid repeated requests
 * Uses Map instead of localStorage to avoid tracking prevention issues
 */
const faviconCache = new Map();

// Cache for domains that consistently fail favicon requests
const failedDomainsCache = new Map();

// Known problematic domains that should skip favicon requests entirely
const problematicDomains = new Set([
  'wix.com',
  'squarespace.com',
  'weebly.com',
]);

// Domains that should skip Google Favicon V2 API (but can use other sources)
const skipGoogleFaviconDomains = new Set([
  'creeksidefinegrillwylietx.com',
  'jerseyjoesdeli.com',
]);

/**
 * Create a fallback icon element when none exists
 * @param {HTMLElement} container - The container to add the fallback icon to
 * @returns {HTMLElement|null} - The created fallback icon element
 */
function createFallbackIcon(container) {
  if (!container) return null;

  try {
    // Create fallback icon element
    const fallbackIcon = document.createElement('i');
    fallbackIcon.className = 'fas fa-utensils text-primary restaurant-fallback-icon';
    fallbackIcon.style.display = 'inline-block';
    fallbackIcon.style.opacity = '1';

    // Determine appropriate size based on container context
    const containerClasses = container.className;
    if (containerClasses.includes('table') || containerClasses.includes('small')) {
      fallbackIcon.style.fontSize = '16px';
      fallbackIcon.classList.add('restaurant-fallback-icon-table');
    } else if (containerClasses.includes('large') || containerClasses.includes('detail')) {
      fallbackIcon.style.fontSize = '32px';
      fallbackIcon.classList.add('restaurant-fallback-icon-large');
    } else if (containerClasses.includes('dashboard')) {
      fallbackIcon.style.fontSize = '24px';
      fallbackIcon.classList.add('restaurant-fallback-icon-dashboard');
    } else {
      fallbackIcon.style.fontSize = '20px';
    }

    // Add the fallback icon to the container
    container.appendChild(fallbackIcon);

    // Debug logging only in debug mode
    if (window.location.search.includes('debug=favicon')) {
      console.debug('Created fallback icon:', fallbackIcon);
    }

    return fallbackIcon;
  } catch (error) {
    console.warn('Error creating fallback icon:', error);
    return null;
  }
}

/**
 * Find or create a fallback icon using multiple strategies
 * @param {HTMLImageElement} imgElement - The image element
 * @param {string} fallbackSelector - The fallback selector
 * @returns {HTMLElement|null} - The found or created fallback icon
 */
function findOrCreateFallbackIcon(imgElement, fallbackSelector) {
  let fallbackIcon = null;

  // Strategy 1: Look for sibling fallback icon (most common case)
  fallbackIcon = imgElement.parentElement?.querySelector(fallbackSelector);
  if (fallbackIcon) return fallbackIcon;

  // Strategy 2: Look for fallback icon as next sibling
  fallbackIcon = imgElement.nextElementSibling;
  if (fallbackIcon && fallbackIcon.classList.contains('restaurant-fallback-icon')) {
    return fallbackIcon;
  }

  // Strategy 3: Look for fallback icon as previous sibling
  fallbackIcon = imgElement.previousElementSibling;
  if (fallbackIcon && fallbackIcon.classList.contains('restaurant-fallback-icon')) {
    return fallbackIcon;
  }

  // Strategy 4: Look in parent container with more specific selectors
  if (imgElement.parentElement) {
    const container = imgElement.parentElement;
    const selectors = [
      '.restaurant-fallback-icon',
      '.restaurant-fallback-icon-table',
      '.restaurant-fallback-icon-large',
      '.restaurant-fallback-icon-dashboard',
    ];

    for (const selector of selectors) {
      fallbackIcon = container.querySelector(selector);
      if (fallbackIcon) return fallbackIcon;
    }
  }

  // Strategy 5: Create fallback icon if none exists
  if (imgElement.parentElement) {
    return createFallbackIcon(imgElement.parentElement);
  }

  return null;
}

/**
 * Show a fallback icon with proper styling
 * @param {HTMLElement} fallbackIcon - The fallback icon element
 */
function showFallbackIcon(fallbackIcon) {
  fallbackIcon.style.display = 'inline-block';
  fallbackIcon.classList.remove('d-none');
  fallbackIcon.style.opacity = '1';

  // Debug logging only in debug mode
  if (window.location.search.includes('debug=favicon')) {
    console.debug('Fallback icon shown for favicon error:', fallbackIcon);
  }
}

/**
 * Find the fallback icon associated with an image element
 * @param {HTMLImageElement} imgElement - The image element
 * @returns {HTMLElement|null} - The fallback icon element or null
 */
function findFallbackIcon(imgElement) {
  // Strategy 1: Look for sibling fallback icon
  let fallbackIcon = imgElement.parentElement.querySelector('.restaurant-fallback-icon');

  if (fallbackIcon) {
    return fallbackIcon;
  }

  // Strategy 2: Look for next sibling fallback icon
  fallbackIcon = imgElement.nextElementSibling;
  if (fallbackIcon && fallbackIcon.classList.contains('restaurant-fallback-icon')) {
    return fallbackIcon;
  }

  // Strategy 3: Look for previous sibling fallback icon
  fallbackIcon = imgElement.previousElementSibling;
  if (fallbackIcon && fallbackIcon.classList.contains('restaurant-fallback-icon')) {
    return fallbackIcon;
  }

  // Strategy 4: Look in parent container
  const container = imgElement.closest('.restaurant-favicon, .restaurant-favicon-table');
  if (container) {
    fallbackIcon = container.querySelector('.restaurant-fallback-icon');
    if (fallbackIcon) {
      return fallbackIcon;
    }
  }

  return null;
}

/**
 * Hide a fallback icon
 * @param {HTMLImageElement} imgElement - The image element to find associated fallback for
 */
function hideFallbackIcon(imgElement) {
  // Find the associated fallback icon
  const fallbackIcon = findFallbackIcon(imgElement);

  if (fallbackIcon) {
    fallbackIcon.style.display = 'none';
    fallbackIcon.classList.add('d-none');
    fallbackIcon.style.opacity = '0';

    // Debug logging only in debug mode
    if (window.location.search.includes('debug=favicon')) {
      console.debug('Fallback icon hidden - real favicon loaded:', imgElement.src);
    }
  }
}

/**
 * Handle favicon loading errors with fallback strategies
 * @param {HTMLImageElement} imgElement - The image element that failed to load
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
    if (!showFallback) return;

    const fallbackIcon = findOrCreateFallbackIcon(imgElement, fallbackSelector);

    if (fallbackIcon) {
      showFallbackIcon(fallbackIcon);
    } else {
      console.warn('Fallback icon not found for favicon error - no fallback available');
    }
  } catch (error) {
    console.warn('Error in handleFaviconError:', error);
  }
}

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
    const [domain] = url
      .replace(/^https?:\/\//, '')
      .replace(/^www\./, '')
      .split('/'); // Remove path

    // Handle edge cases
    if (domain.includes('.')) {
      return domain;
    }
    return '';
  } catch {
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
    if (window.location.search.includes('debug=favicon')) {
      console.debug(`Domain "${domain}" found in problematic domains list`);
    }
    return true;
  }

  // Check if root domain is in problematic domains list
  const rootDomain = extractRootDomain(domain);
  if (problematicDomains.has(rootDomain)) {
    if (window.location.search.includes('debug=favicon')) {
      console.debug(`Root domain "${rootDomain}" found in problematic domains list for "${domain}"`);
    }
    return true;
  }

  // Check if domain has consistently failed favicon requests
  const failedCount = failedDomainsCache.get(domain) || 0;
  if (failedCount >= 3) {
    if (window.location.search.includes('debug=favicon')) {
      console.debug(`Domain "${domain}" has failed ${failedCount} times, skipping`);
    }
    return true;
  }

  if (window.location.search.includes('debug=favicon')) {
    console.debug(`Domain "${domain}" (root: "${rootDomain}") is not problematic, proceeding with favicon request`);
  }
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
 * Try to load favicon from a specific source (Google-style seamless approach)
 * @param {string} src - The favicon URL
 * @param {number} timeout - Timeout in milliseconds
 * @returns {Promise<string|null>} - Returns the URL if successful, null if failed
 */
function tryFaviconSource(src, timeout = 2500) {
  return new Promise((resolve) => {
    if (!src || typeof src !== 'string') {
      resolve(null);
      return;
    }

    const timeoutId = setTimeout(() => resolve(null), timeout);

    // Create a test image to check if the favicon loads
    const testImg = new Image();

    // Suppress error logging for expected favicon 404s
    testImg.addEventListener('error', (event) => {
      // Prevent the 404 error from appearing in console
      event.preventDefault();
      event.stopPropagation();
      event.stopImmediatePropagation();
      clearTimeout(timeoutId);
      resolve(null); // Failed, try next source
    });

    testImg.onload = () => {
      clearTimeout(timeoutId);
      resolve(src); // Return the successful URL
    };

    // Start loading
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
  if (shouldSkipFaviconRequest(domain)) {
    // Only log in debug mode to reduce console noise
    if (window.location.search.includes('debug=favicon')) {
      console.debug(`Skipping favicon request for problematic domain: ${domain}`);
    }
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
    // Check if this domain should skip Google Favicon V2 API
    const shouldSkipGoogle = skipGoogleFaviconDomains.has(domain);

    // Filter out sources to skip
    const sourcesToTry = FAVICON_SOURCES.filter((source) =>
      !(shouldSkipGoogle && source.name === 'google-favicon-v2'),
    );

    // Try each favicon source in sequence until one works
    const tryNextSource = async(index) => {
      if (index >= sourcesToTry.length) {
        return false; // All sources failed
      }

      const source = sourcesToTry[index];
      const src = source.url(domain);
      const result = await tryFaviconSource(src, source.timeout);

      if (result) {
        // Success! Cache and apply the favicon
        faviconCache.set(cacheKey, { success: true, src: result });
        imgElement.src = result;
        imgElement.style.opacity = '1';
        return true;
      }

      // Try next source
      return tryNextSource(index + 1);
    };

    const success = await tryNextSource(0);
    if (success) {
      return; // Exit early on success
    }

    // If we get here, all sources failed
    faviconCache.set(cacheKey, { success: false, src: '' });
    markDomainAsFailed(domain);
    handleFaviconError(imgElement, { fallbackSelector, hideImage, showFallback });

  } catch (error) {
    console.error('Error loading favicon with fallback:', error);
    handleFaviconError(imgElement, { fallbackSelector, hideImage, showFallback });
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
    imgElement.style.display = 'inline-block';

    // Hide the fallback icon since real favicon loaded successfully
    hideFallbackIcon(imgElement);

    // Log success for debugging
    if (window.location.search.includes('debug=favicon')) {
      console.debug('✅ Favicon loaded successfully:', imgElement.src);
    }
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

        // Handle already loaded images immediately
        if (favicon.complete && favicon.naturalWidth > 0 && !favicon.loading) {
          handleFaviconLoad(favicon);
        }

        // Handle lazy loading - check if image is in viewport and loaded
        if (favicon.loading === 'lazy') {
          // Use Intersection Observer to detect when lazy image loads
          if ('IntersectionObserver' in window) {
            const observer = new IntersectionObserver((entries) => {
              entries.forEach((entry) => {
                if (entry.isIntersecting && entry.target.complete && entry.target.naturalWidth > 0) {
                  handleFaviconLoad(entry.target);
                  observer.unobserve(entry.target);
                }
              });
            });
            observer.observe(favicon);
          }
        }

        // Use requestAnimationFrame instead of setTimeout for better performance
        const checkLazyLoaded = () => {
          if (favicon.complete && favicon.naturalWidth > 0) {
            handleFaviconLoad(favicon);
            return true;
          }
          return false;
        };

        // Check immediately and with requestAnimationFrame for deferred checks
        if (!checkLazyLoaded()) {
          requestAnimationFrame(() => {
            if (!checkLazyLoaded()) {
              requestAnimationFrame(checkLazyLoaded);
            }
          });
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
  failedDomainsCache.clear();
}

/**
 * Enable debug mode for favicon handling
 * Adds ?debug=favicon to URL to enable detailed logging
 */
export function enableFaviconDebugMode() {
  const url = new URL(window.location);
  if (!url.searchParams.has('debug') || url.searchParams.get('debug') !== 'favicon') {
    url.searchParams.set('debug', 'favicon');
    window.location.href = url.toString();
  }
}

/**
 * Get favicon handling statistics for debugging
 * @returns {Object} - Statistics about favicon handling
 */
export function getFaviconStats() {
  return {
    cacheSize: faviconCache.size,
    failedDomainsCount: failedDomainsCache.size,
    problematicDomainsCount: problematicDomains.size,
    cacheEntries: Array.from(faviconCache.entries()),
    failedDomains: Array.from(failedDomainsCache.keys()),
  };
}

/**
 * Test favicon handling for a specific domain
 * @param {string} domain - The domain to test
 * @returns {Promise<Object>} - Test results
 */
export async function testFaviconForDomain(domain) {
  const results = {
    domain,
    sources: [],
    success: false,
    workingSource: null,
  };

  // Test all sources in parallel to avoid await in loop
  const sourcePromises = FAVICON_SOURCES.map(async(source) => {
    try {
      const src = source.url(domain);
      const loaded = await tryFaviconSource(null, src, source.timeout);

      return {
        name: source.name,
        url: src,
        success: loaded,
      };
    } catch (error) {
      return {
        name: source.name,
        url: source.url(domain),
        success: false,
        error: error.message,
      };
    }
  });

  const sourceResults = await Promise.all(sourcePromises);
  results.sources = sourceResults;

  // Find the first successful source
  for (const source of sourceResults) {
    if (source.success && !results.success) {
      results.success = true;
      results.workingSource = source.name;
      break;
    }
  }

  return results;
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
    domains: Array.from(failedDomainsCache.entries()),
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
    failedSources: [],
  };

  for (const source of FAVICON_SOURCES) {
    const url = source.url(domain);
    const startTime = Date.now();

    try {
      // eslint-disable-next-line no-await-in-loop
      const success = await tryFaviconSource(null, url, source.timeout);
      const duration = Date.now() - startTime;

      const result = {
        name: source.name,
        url,
        success,
        duration,
        timeout: source.timeout,
      };

      results.sources.push(result);

      if (success) {
        results.workingSources.push(result);
      } else {
        results.failedSources.push(result);
      }
    } catch {
      results.sources.push({
        name: source.name,
        url,
        success: false,
        error: error.message,
        duration: Date.now() - startTime,
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
    entries: [],
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
      src: value.src,
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
  window.addEventListener('error', (event) => {
    if (event.message && event.message.includes('CORS') &&
        (event.filename && event.filename.includes('favicon.ico'))) {
      event.preventDefault(); // Prevent the error from being logged
      return false;
    }
  }, true);

  // Add a more aggressive error listener for network errors
  window.addEventListener('error', (event) => {
    if (event.target && event.target.tagName === 'IMG' &&
        event.target.src && (
      event.target.src.includes('t1.gstatic.com/faviconV2') ||
          event.target.src.includes('t3.gstatic.com/faviconV2') ||
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
  window.onerror = function(message, _source, _lineno, _colno, _error, ...args) {
    if (message && (
      message.includes('t1.gstatic.com/faviconV2') ||
        message.includes('t3.gstatic.com/faviconV2') ||
        message.includes('favicon.ico') ||
        message.includes('CORS') ||
        message.includes('404 (Not Found)')
    )) {
      return true; // Suppress the error
    }
    if (originalError) {
      return originalError.apply(this, [message, _source, _lineno, _colno, _error, ...args]);
    }
    return false;
  };

  // Override the browser's native error logging for network requests
  const originalUnhandledRejection = window.onunhandledrejection;
  window.onunhandledrejection = function(event, ...args) {
    if (event.reason && event.reason.message && (
      event.reason.message.includes('t1.gstatic.com/faviconV2') ||
        event.reason.message.includes('t3.gstatic.com/faviconV2') ||
        event.reason.message.includes('favicon.ico') ||
        event.reason.message.includes('404')
    )) {
      event.preventDefault();
      return false;
    }
    if (originalUnhandledRejection) {
      return originalUnhandledRejection.apply(this, [event, ...args]);
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
        (message.includes('t3.gstatic.com/faviconV2') && message.includes('404')) ||
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
        (message.includes('t3.gstatic.com/faviconV2') && message.includes('404')) ||
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
        (message.includes('t3.gstatic.com/faviconV2') && message.includes('404')) ||
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
      const [url] = args;
      if (typeof url === 'string' && (
        url.includes('google.com/s2/favicons') ||
          url.includes('t1.gstatic.com/faviconV2') ||
          url.includes('t3.gstatic.com/faviconV2') ||
          url.includes('favicons.githubusercontent.com') ||
          url.includes('logo.clearbit.com') ||
          url.includes('favicon.ico')
      )) {
        // Suppress network errors for favicon requests
        return originalFetch.apply(this, args).catch((error) => {
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
        url.includes('t3.gstatic.com/faviconV2') ||
        url.includes('google.com/s2/favicons') ||
        url.includes('favicons.githubusercontent.com') ||
        url.includes('logo.clearbit.com') ||
        url.includes('favicon.ico')
    )) {
      // Suppress errors for favicon requests
      this.addEventListener('error', (event) => {
        event.preventDefault();
        event.stopPropagation();
      });
    }
    return originalXHROpen.apply(this, [method, url, ...args]);
  };
}

// Standard initialization function
function initializeFaviconSystem() {
  // Suppress CORS errors for favicon requests
  suppressFaviconCORSErrors();

  // Add global error suppression for favicon 404s - capture phase
  window.addEventListener('error', (event) => {
    if (event.target && event.target.tagName === 'IMG' &&
        event.target.src && (event.target.src.includes('faviconV2') || event.target.src.includes('favicon'))) {
      // Suppress all favicon-related 404 errors
      event.preventDefault();
      event.stopPropagation();
      event.stopImmediatePropagation();
      return false;
    }
  }, true);

  // Also suppress unhandled promise rejections for favicon errors
  window.addEventListener('unhandledrejection', (event) => {
    if (event.reason && event.reason.message &&
        event.reason.message.includes('favicon')) {
      event.preventDefault();
    }
  });

  // Initialize favicon handling for all favicon elements
  initializeRobustFaviconHandling('.restaurant-favicon');
  initializeRobustFaviconHandling('.restaurant-favicon-table');

  // Debug logging (only in debug mode)
  if (window.location.search.includes('debug=favicon')) {
    console.debug('🔧 Favicon Handler v3.6.0 initialized - Modern Google Favicon V2 API Enabled');
  }
}

// Note: Favicon system is now initialized by main.js
// Auto-initialization removed to prevent conflicts

// Export for global access
window.RobustFaviconHandler = {
  loadWithFallback: loadFaviconWithFallback,
  handleError: handleFaviconError,
  handleLoad: handleFaviconLoad,
  initialize: initializeRobustFaviconHandling,
  initializeSystem: initializeFaviconSystem,
  clearCache: clearFaviconCache,
  clearFailedDomainsCache,
  getCacheStats: getFaviconCacheStats,
  getFailedDomainsCacheStats,
};
