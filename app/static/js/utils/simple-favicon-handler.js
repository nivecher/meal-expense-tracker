/**
 * Simple Favicon Handler - Web Standards Compliant
 * Pure frontend favicon loading following browser standards
 * Following TIGER principles: Safety, Performance, Developer Experience
 */

/**
 * Cache for favicon results to avoid repeated requests
 */
const faviconCache = new Map();

/**
 * Domain deduplication to prevent multiple requests for same domain
 */
const requestsInFlight = new Map();

/**
 * Standard favicon sources in order of reliability
 */
const FAVICON_SOURCES = [
  {
    name: 'direct',
    url: (domain) => `https://${domain}/favicon.ico`,
    timeout: 2000,
  },
  {
    name: 'google',
    url: (domain) => `https://www.google.com/s2/favicons?domain=${domain}&sz=32`,
    timeout: 3000,
  },
  {
    name: 'duckduckgo',
    url: (domain) => `https://icons.duckduckgo.com/ip3/${domain}.ico`,
    timeout: 3000,
  },
];

/**
 * Extract clean domain from URL
 * @param {string} url - Website URL
 * @returns {string} - Clean domain
 */
function extractDomain(url) {
  if (!url || typeof url !== 'string') {
    return '';
  }

  try {
    // Handle URLs without protocol
    const cleanUrl = url.startsWith('http') ? url : `https://${url}`;
    const domain = new URL(cleanUrl).hostname.toLowerCase();

    // Remove www prefix
    return domain.startsWith('www.') ? domain.slice(4) : domain;
  } catch (error) {
    console.warn('Error extracting domain:', error.message);
    return '';
  }
}

/**
 * Test if favicon loads from a specific source
 * @param {string} src - Favicon URL to test
 * @param {number} timeout - Timeout in milliseconds
 * @returns {Promise<boolean>} - Whether favicon loads successfully
 */
function testFaviconSource(src, timeout = 3000) {
  return new Promise((resolve) => {
    const timeoutId = setTimeout(() => resolve(false), timeout);

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
 * Load favicon with simple fallback strategy
 * @param {HTMLImageElement} imgElement - Image element to update
 * @param {string} website - Website URL
 * @param {Object} options - Configuration options
 */
export async function loadFaviconWithFallback(imgElement, website, options = {}) {
  const {
    fallbackSelector = '.restaurant-fallback-icon',
    hideImage = true,
    showFallback = true,
    size = 32,
  } = options;

  // Input validation
  if (!imgElement || !(imgElement instanceof HTMLImageElement)) {
    console.warn('Invalid image element provided');
    return;
  }

  if (!website || typeof website !== 'string') {
    console.warn('Invalid website URL provided');
    return;
  }

  const domain = extractDomain(website);
  if (!domain) {
    console.warn('Could not extract domain from website:', website);
    showFallbackIcon(imgElement, fallbackSelector, hideImage, showFallback);
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
      showFallbackIcon(imgElement, fallbackSelector, hideImage, showFallback);
      return;
    }
  }

  // Check if request already in progress for this domain
  if (requestsInFlight.has(domain)) {
    try {
      const result = await requestsInFlight.get(domain);
      if (result) {
        imgElement.src = result;
        imgElement.style.opacity = '1';
      } else {
        showFallbackIcon(imgElement, fallbackSelector, hideImage, showFallback);
      }
    } catch (error) {
      showFallbackIcon(imgElement, fallbackSelector, hideImage, showFallback);
    }
    return;
  }

  // Create new request
  const requestPromise = loadFaviconFromSources(domain);
  requestsInFlight.set(domain, requestPromise);

  try {
    const faviconSrc = await requestPromise;

    if (faviconSrc) {
      imgElement.src = faviconSrc;
      imgElement.style.opacity = '1';
      // Cache success
      faviconCache.set(cacheKey, { success: true, src: faviconSrc });
    } else {
      showFallbackIcon(imgElement, fallbackSelector, hideImage, showFallback);
      // Cache failure to avoid retries
      faviconCache.set(cacheKey, { success: false });
    }
  } catch (error) {
    console.warn('Favicon loading failed:', error.message);
    showFallbackIcon(imgElement, fallbackSelector, hideImage, showFallback);
    faviconCache.set(cacheKey, { success: false });
  } finally {
    requestsInFlight.delete(domain);
  }
}

/**
 * Try loading favicon from multiple sources
 * @param {string} domain - Clean domain name
 * @returns {Promise<string|null>} - Working favicon URL or null
 */
async function loadFaviconFromSources(domain) {
  for (const source of FAVICON_SOURCES) {
    try {
      const src = source.url(domain);
      const success = await testFaviconSource(src, source.timeout);

      if (success) {
        return src;
      }
    } catch (error) {
      // Continue to next source
      continue;
    }
  }

  return null;
}

/**
 * Show fallback icon when favicon fails
 * @param {HTMLImageElement} imgElement - Failed image element
 * @param {string} fallbackSelector - CSS selector for fallback icon
 * @param {boolean} hideImage - Whether to hide failed image
 * @param {boolean} showFallback - Whether to show fallback icon
 */
function showFallbackIcon(imgElement, fallbackSelector, hideImage, showFallback) {
  try {
    if (hideImage) {
      imgElement.style.display = 'none';
    }

    if (showFallback) {
      const container = imgElement.parentElement;
      if (container) {
        const fallbackIcon = container.querySelector(fallbackSelector);
        if (fallbackIcon) {
          fallbackIcon.style.display = 'inline-block';
          fallbackIcon.classList.remove('d-none');
        }
      }
    }
  } catch (error) {
    console.error('Error showing fallback icon:', error);
  }
}

/**
 * Initialize favicon handling for all restaurant favicons
 * @param {string} selector - CSS selector for favicon containers
 */
export function initializeFaviconHandling(selector = '.restaurant-favicon') {
  if (!selector || typeof selector !== 'string') {
    console.warn('Invalid selector provided');
    return;
  }

  try {
    const favicons = document.querySelectorAll(selector);

    // Process favicons with staggered loading to prevent overwhelming
    favicons.forEach((favicon, index) => {
      setTimeout(() => {
        try {
          const website = favicon.dataset.website;
          if (website) {
            loadFaviconWithFallback(favicon, website, {
              size: favicon.dataset.size || 32,
            });
          }
        } catch (error) {
          console.error(`Error initializing favicon ${index}:`, error);
        }
      }, index * 50); // 50ms stagger between favicon loads
    });

  } catch (error) {
    console.error('Error initializing favicon handling:', error);
  }
}

/**
 * Clear favicon cache (useful for testing)
 */
export function clearFaviconCache() {
  faviconCache.clear();
  requestsInFlight.clear();
}

// Auto-initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
  initializeFaviconHandling('.restaurant-favicon');
  initializeFaviconHandling('.restaurant-favicon-table');
});
