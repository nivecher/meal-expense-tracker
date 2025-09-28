/**
 * Performance Optimization Utilities
 *
 * Provides utilities to prevent forced reflow and improve JavaScript performance
 * by batching DOM operations and using efficient patterns.
 */

/**
 * Batches DOM reads and writes to prevent forced reflow
 * @param {Function} readCallback - Function that performs DOM reads
 * @param {Function} writeCallback - Function that performs DOM writes
 */
function batchDOMOperations(readCallback, writeCallback) {
  // Perform all reads first
  const readResults = readCallback();

  // Use requestAnimationFrame to batch writes
  requestAnimationFrame(() => {
    writeCallback(readResults);
  });
}

/**
 * Debounces function calls to prevent excessive execution
 * @param {Function} func - Function to debounce
 * @param {number} wait - Wait time in milliseconds
 * @param {boolean} immediate - Whether to call immediately on first invocation
 * @returns {Function} Debounced function
 */
function debounce(func, wait, immediate = false) {
  let timeout;
  return function executedFunction(...args) {
    const later = () => {
      timeout = null;
      if (!immediate) func.apply(this, args);
    };
    const callNow = immediate && !timeout;
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
    if (callNow) func.apply(this, args);
  };
}

/**
 * Throttles function calls to limit execution frequency
 * @param {Function} func - Function to throttle
 * @param {number} limit - Time limit in milliseconds
 * @returns {Function} Throttled function
 */
function throttle(func, limit) {
  let inThrottle;
  return function executedFunction(...args) {
    if (!inThrottle) {
      func.apply(this, args);
      inThrottle = true;
      setTimeout(() => {
        inThrottle = false;
      }, limit);
    }
  };
}

/**
 * Creates a DocumentFragment for efficient DOM manipulation
 * @param {Function} buildCallback - Function that builds DOM elements
 * @returns {DocumentFragment} Document fragment with built elements
 */
function createDocumentFragment(buildCallback) {
  const fragment = document.createDocumentFragment();
  const elements = buildCallback();

  if (Array.isArray(elements)) {
    elements.forEach((element) => fragment.appendChild(element));
  } else {
    fragment.appendChild(elements);
  }

  return fragment;
}

/**
 * Safely measures element dimensions without causing reflow
 * @param {Element} element - Element to measure
 * @returns {Object} Object with width, height, top, left properties
 */
function measureElement(element) {
  return batchDOMOperations(
    () => ({
      width: element.offsetWidth,
      height: element.offsetHeight,
      top: element.offsetTop,
      left: element.offsetLeft,
      scrollTop: element.scrollTop,
      scrollLeft: element.scrollLeft,
    }),
    (measurements) => measurements,
  );
}

/**
 * Optimizes scroll event handling with passive listeners
 * @param {Element} element - Element to attach scroll listener to
 * @param {Function} callback - Scroll callback function
 * @param {number} throttleMs - Throttle time in milliseconds (default: 16ms for 60fps)
 */
function addOptimizedScrollListener(element, callback, throttleMs = 16) {
  const throttledCallback = throttle(callback, throttleMs);

  element.addEventListener('scroll', throttledCallback, {
    passive: true,
    capture: false,
  });

  return () => element.removeEventListener('scroll', throttledCallback);
}

/**
 * Preloads images to prevent layout shifts
 * @param {string[]} imageUrls - Array of image URLs to preload
 * @returns {Promise} Promise that resolves when all images are loaded
 */
function preloadImages(imageUrls) {
  const promises = imageUrls.map((url) => {
    return new Promise((resolve, reject) => {
      const img = new Image();
      img.onload = resolve;
      img.onerror = reject;
      img.src = url;
    });
  });

  return Promise.all(promises);
}

/**
 * Uses CSS classes instead of direct style manipulation for better performance
 * @param {Element} element - Element to style
 * @param {string} className - CSS class name to toggle
 * @param {boolean} add - Whether to add or remove the class
 */
function toggleStyleClass(element, className, add) {
  if (add) {
    element.classList.add(className);
  } else {
    element.classList.remove(className);
  }
}

// Export utilities for use in other modules
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    batchDOMOperations,
    debounce,
    throttle,
    createDocumentFragment,
    measureElement,
    addOptimizedScrollListener,
    preloadImages,
    toggleStyleClass,
  };
} else {
  // Make utilities available globally
  window.PerformanceOptimizer = {
    batchDOMOperations,
    debounce,
    throttle,
    createDocumentFragment,
    measureElement,
    addOptimizedScrollListener,
    preloadImages,
    toggleStyleClass,
  };
}
