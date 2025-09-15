/**
 * Lazy loading optimizer utility
 * Removes lazy loading from critical images to reduce browser warnings
 * while maintaining performance benefits for non-critical images
 */

function isAboveTheFold(element) {
  const rect = element.getBoundingClientRect();
  const viewportHeight = window.innerHeight || document.documentElement.clientHeight;
  return rect.top < viewportHeight;
}

function optimizeImage(img) {
  if (isAboveTheFold(img)) {
    img.removeAttribute('loading');
    img.classList.add('lazy-optimized');

    if (window.location.search.includes('debug=true')) {
      console.log('Optimized lazy loading for dynamic image:', img.src || img.alt);
    }
  }
}

function setupDynamicOptimization() {
  // Watch for dynamically added images
  const observer = new MutationObserver((mutations) => {
    mutations.forEach((mutation) => {
      mutation.addedNodes.forEach((node) => {
        if (node.nodeType === Node.ELEMENT_NODE) {
          // Check if the added node is an image
          if (node.tagName === 'IMG' && node.hasAttribute('loading') && node.getAttribute('loading') === 'lazy') {
            optimizeImage(node);
          }

          // Check for images within the added node
          const images = node.querySelectorAll('img[loading="lazy"]');
          images.forEach(optimizeImage);
        }
      });
    });
  });

  // Start observing
  observer.observe(document.body, {
    childList: true,
    subtree: true,
  });

  // Clean up observer after 30 seconds to avoid memory leaks
  setTimeout(() => {
    observer.disconnect();
  }, 30000);
}

export function optimizeLazyLoading() {
  // Define critical image selectors (above-the-fold images)
  const criticalSelectors = [
    'img[loading="lazy"]:first-of-type', // First image in any container
    '.restaurant-card img[loading="lazy"]:first-child', // First restaurant card image
    '.avatar-img[loading="lazy"]', // User avatars (usually above fold)
    '.navbar img[loading="lazy"]', // Navigation images
    '.hero img[loading="lazy"]', // Hero section images
    '.above-fold img[loading="lazy"]', // Explicitly marked above-fold images
  ];

  // Find and optimize critical images
  criticalSelectors.forEach((selector) => {
    const images = document.querySelectorAll(selector);
    images.forEach((img) => {
      // Remove lazy loading from critical images
      img.removeAttribute('loading');

      // Add a class to track optimization
      img.classList.add('lazy-optimized');

      // Log optimization (only in debug mode)
      if (window.location.search.includes('debug=true')) {
        console.log('Optimized lazy loading for critical image:', img.src || img.alt);
      }
    });
  });

  // Handle dynamically added images
  setupDynamicOptimization();
}
