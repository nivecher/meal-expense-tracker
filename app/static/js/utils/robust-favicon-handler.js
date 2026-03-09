/**
 * Robust Favicon Handler Utility
 * Loads favicons using canonical host candidates (www/apex) and multiple sources.
 * Backend canonicalizes website URLs; this handler tries each host candidate and source until one works.
 * When data-favicon-url is set (e.g. merchant override), that URL is used directly.
 */

/**
 * Favicon source order: try more reliable sources first to reduce 404s.
 * Google Favicon V2 is last as it often 404s for many domains.
 */
const FAVICON_SOURCES = [
  { name: 'duckduckgo', url: (domain) => `https://icons.duckduckgo.com/ip3/${domain}.ico`, timeout: 2500 },
  { name: 'direct', url: (domain) => `https://${domain}/favicon.ico`, timeout: 2000 },
  { name: 'google-legacy', url: (domain) => `https://www.google.com/s2/favicons?domain=${domain}&sz=64`, timeout: 2500 },
  {
    name: 'google-favicon-v2',
    url: (domain) =>
      `https://t3.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL&url=https://${domain}&size=64`,
    timeout: 2500,
  },
];

const faviconCache = new Map();
const failedDomainsCache = new Map();

/** Domains that 404 from all sources; skip favicon requests entirely. */
const problematicDomains = new Set(['wix.com', 'squarespace.com', 'weebly.com']);

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
  const { fallbackSelector = '.restaurant-fallback-icon', hideImage = true, showFallback = true } = options;

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
 * Derive host from URL (lowercase, no path).
 * @param {string} url - Website URL
 * @returns {string} - Host or empty string
 */
function extractHost(url) {
  if (!url || typeof url !== 'string') return '';
  try {
    const withoutProtocol = url.replace(/^https?:\/\//, '').split('/')[0] || '';
    const host = withoutProtocol.toLowerCase();
    return host && host.includes('.') ? host : '';
  } catch {
    return '';
  }
}

/**
 * Return bounded list of host candidates for favicon resolution (canonical host plus www/apex alternate).
 * Matches backend get_favicon_host_candidates so sites like chick-fil-a.com try both www and apex.
 * @param {string} website - Canonical website URL
 * @returns {string[]} - Up to two host strings to try
 */
function getFaviconHostCandidates(website) {
  const host = extractHost(website);
  if (!host) return [];
  const candidates = [host];
  if (host.startsWith('www.')) {
    const apex = host.slice(4);
    if (apex && !candidates.includes(apex)) candidates.push(apex);
  } else {
    const withWww = `www.${host}`;
    if (!candidates.includes(withWww)) candidates.push(withWww);
  }
  return candidates.slice(0, 2);
}

/**
 * Extract root domain for skip-list checks (e.g. example.co.uk).
 */
function extractRootDomain(domain) {
  if (!domain || typeof domain !== 'string') return domain;
  const parts = domain.split('.');
  return parts.length >= 2 ? parts.slice(-2).join('.') : domain;
}

/**
 * Check if host should skip favicon requests (problematic root or previously failed).
 */
function shouldSkipFaviconRequest(host) {
  if (problematicDomains.has(host)) return true;
  if (problematicDomains.has(extractRootDomain(host))) return true;
  if ((failedDomainsCache.get(host) || 0) >= 1) return true;
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
 * Load favicon using host candidates (www/apex) and source fallback.
 * @param {HTMLImageElement} imgElement - Image element to update
 * @param {string} website - Canonical website URL (backend-normalized)
 * @param {Object} options - Options (fallbackSelector, hideImage, showFallback, size)
 */
export async function loadFaviconWithFallback(imgElement, website, options = {}) {
  const { fallbackSelector = '.restaurant-fallback-icon', hideImage = true, showFallback = true, size = 32 } = options;

  if (!imgElement || !(imgElement instanceof HTMLImageElement)) {
    console.warn('Invalid image element provided to loadFaviconWithFallback');
    return;
  }
  if (!website || typeof website !== 'string') {
    handleFaviconError(imgElement, { fallbackSelector, hideImage, showFallback });
    return;
  }

  const candidates = getFaviconHostCandidates(website);
  if (candidates.length === 0) {
    handleFaviconError(imgElement, { fallbackSelector, hideImage, showFallback });
    return;
  }

  const cacheKey = `${candidates[0]}-${size}`;
  if (shouldSkipFaviconRequest(candidates[0])) {
    handleFaviconError(imgElement, { fallbackSelector, hideImage, showFallback });
    return;
  }

  if (faviconCache.has(cacheKey)) {
    const cached = faviconCache.get(cacheKey);
    if (cached.success) {
      imgElement.src = cached.src;
      imgElement.style.opacity = '1';
      return;
    }
    handleFaviconError(imgElement, { fallbackSelector, hideImage, showFallback });
    return;
  }

  try {
    for (const domain of candidates) {
      for (const source of FAVICON_SOURCES) {
        const src = source.url(domain);
        // Sequential try: stop on first success; parallel would change behavior
        const result = await tryFaviconSource(src, source.timeout); // eslint-disable-line no-await-in-loop
        if (result) {
          faviconCache.set(cacheKey, { success: true, src: result });
          imgElement.src = result;
          imgElement.style.opacity = '1';
          return;
        }
      }
    }
    faviconCache.set(cacheKey, { success: false, src: '' });
    markDomainAsFailed(candidates[0]);
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

    faviconsToProcess.forEach((favicon) => {
      try {
        const explicitUrl = favicon.dataset.faviconUrl;
        const { website } = favicon.dataset;

        if (explicitUrl) {
          favicon.src = explicitUrl;
          if (!favicon.onload) {
            favicon.onload = () => handleFaviconLoad(favicon);
          }
          if (!favicon.onerror) {
            favicon.onerror = () => handleFaviconError(favicon);
          }
          return;
        }

        if (website) {
          loadFaviconWithFallback(favicon, website, {
            size: favicon.dataset.size || 32,
          });
        } else {
          if (!favicon.onerror) {
            favicon.onerror = () => handleFaviconError(favicon);
          }
        }

        if (!favicon.onload) {
          favicon.onload = () => handleFaviconLoad(favicon);
        }

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
      const loaded = await tryFaviconSource(src, source.timeout);

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
      const success = await tryFaviconSource(url, source.timeout);
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
    } catch (error) {
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

/** Minimal suppression: stop IMG load errors for our favicon URLs from bubbling to console. */
function suppressFaviconLoadErrors() {
  const faviconPatterns = [
    'duckduckgo.com',
    'google.com/s2/favicons',
    'gstatic.com/faviconV2',
  ];
  window.addEventListener(
    'error',
    (event) => {
      if (
        event.target &&
        event.target.tagName === 'IMG' &&
        typeof event.target.src === 'string' &&
        faviconPatterns.some((p) => event.target.src.includes(p))
      ) {
        event.preventDefault();
        event.stopPropagation();
        return false;
      }
    },
    true,
  );
}

export function initializeFaviconSystem() {
  suppressFaviconLoadErrors();
  initializeRobustFaviconHandling('.restaurant-favicon');
  initializeRobustFaviconHandling('.restaurant-favicon-table');
  if (window.location.search.includes('debug=favicon')) {
    console.debug('Favicon handler initialized (host candidates + source fallback)');
  }
}

// Note: Favicon system is now initialized by main.js
// Auto-initialization removed to prevent conflicts

export { getFaviconHostCandidates };

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
  getFaviconHostCandidates,
};
