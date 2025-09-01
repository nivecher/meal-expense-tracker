/**
 * Cuisine badge component for rendering cuisine badges with colors and icons
 * Automatically enhances .cuisine-badge elements on page load
 * Following TIGER principles: Safety, Performance, Developer Experience
 */

import {
  getCuisineData,
  getCuisineColor,
  getCuisineIcon,
  createCuisineBadge,
} from '../utils/cuisine-formatter.js';

/**
 * Initialize cuisine badges on the page
 * Finds all .cuisine-badge elements and enhances them with colors and icons
 *
 * @param {string} selector - CSS selector for badge elements (default: '.cuisine-badge')
 * @param {Object} options - Configuration options
 * @param {boolean} options.showIcon - Whether to show icons (default: true)
 * @param {boolean} options.preserveExisting - Keep existing content as fallback (default: true)
 */
export function initializeCuisineBadges(selector = '.cuisine-badge', options = {}) {
  const { showIcon = true, preserveExisting = true } = options;

  // Input validation - safety first
  if (!selector || typeof selector !== 'string') {
    console.warn('Invalid selector provided to initializeCuisineBadges');
    return;
  }

  try {
    const badges = document.querySelectorAll(selector);

    // Enforce bounds to prevent excessive processing
    if (badges.length > 1000) {
      console.warn('Too many cuisine badges found, limiting to first 1000');
    }

    const badgesToProcess = Array.from(badges).slice(0, 1000);
    console.log(`Initializing ${badgesToProcess.length} cuisine badges`);

    badgesToProcess.forEach((badge, index) => {
      try {
        enhanceCuisineBadge(badge, { showIcon, preserveExisting });
      } catch (error) {
        console.error(`Error enhancing cuisine badge ${index}:`, error);
      }
    });

  } catch (error) {
    console.error('Error initializing cuisine badges:', error);
  }
}

/**
 * Enhance a single cuisine badge element with colors and icons
 *
 * @param {HTMLElement} badgeElement - The badge element to enhance
 * @param {Object} options - Enhancement options
 * @param {boolean} options.showIcon - Whether to show icons
 * @param {boolean} options.preserveExisting - Keep existing content as fallback
 */
export function enhanceCuisineBadge(badgeElement, options = {}) {
  const { showIcon = true, preserveExisting = true } = options;

  // Input validation
  if (!badgeElement || !(badgeElement instanceof HTMLElement)) {
    console.warn('Invalid badge element provided');
    return;
  }

  // Get cuisine name from data attribute
  const cuisineName = badgeElement.dataset.cuisine;
  if (!cuisineName || typeof cuisineName !== 'string') {
    console.warn('No cuisine data found on badge element');
    return;
  }

  // Enforce bounds
  if (cuisineName.length > 100) {
    console.warn('Cuisine name too long, skipping enhancement');
    return;
  }

  try {
    // Get cuisine data
    const cuisineData = getCuisineData(cuisineName.trim());

    if (cuisineData) {
      // Create enhanced badge HTML
      const enhancedBadgeHtml = createCuisineBadge(cuisineData.name, {
        showIcon,
        className: 'enhanced-cuisine-badge'
      });

      // Replace content with enhanced version
      badgeElement.innerHTML = enhancedBadgeHtml;

      // Add enhancement indicator
      badgeElement.classList.add('cuisine-enhanced');

      console.log(`Enhanced cuisine badge for: ${cuisineData.name}`);
    } else if (preserveExisting) {
      // Keep existing content but add styling for unknown cuisines
      const existingBadge = badgeElement.querySelector('.badge');
      if (existingBadge) {
        // Import colors from centralized constants (fallback to hardcoded if import fails)
        const defaultGray = window.MEAL_TRACKER_COLORS?.gray || '#6c757d';
        existingBadge.style.backgroundColor = `${defaultGray}20`;
        existingBadge.style.color = defaultGray;
        existingBadge.style.borderColor = `${defaultGray}40`;

        // Add question icon for unknown cuisines if showIcon is true
        if (showIcon && !existingBadge.querySelector('i')) {
          const icon = document.createElement('i');
          icon.className = 'fas fa-question me-1';
          existingBadge.insertBefore(icon, existingBadge.firstChild);
        }
      }

      badgeElement.classList.add('cuisine-unknown');
      console.log(`Unknown cuisine: ${cuisineName}, preserved existing content`);
    }

  } catch (error) {
    console.error(`Error enhancing badge for cuisine "${cuisineName}":`, error);
  }
}

/**
 * Create and return a new cuisine badge element
 *
 * @param {string} cuisineName - Name of the cuisine
 * @param {Object} options - Badge creation options
 * @param {boolean} options.showIcon - Whether to show icons (default: true)
 * @param {string} options.className - Additional CSS classes
 * @returns {HTMLElement|null} Created badge element or null on error
 */
export function createCuisineBadgeElement(cuisineName, options = {}) {
  const { showIcon = true, className = '' } = options;

  // Input validation
  if (!cuisineName || typeof cuisineName !== 'string') {
    return null;
  }

  // Enforce bounds
  if (cuisineName.length > 100) {
    return null;
  }

  try {
    // Create container element
    const container = document.createElement('span');
    container.className = `cuisine-badge ${className}`.trim();
    container.dataset.cuisine = cuisineName;

    // Get badge HTML
    const badgeHtml = createCuisineBadge(cuisineName, { showIcon });
    container.innerHTML = badgeHtml;

    // Add enhancement indicator
    container.classList.add('cuisine-enhanced');

    return container;

  } catch (error) {
    console.error(`Error creating cuisine badge element for "${cuisineName}":`, error);
    return null;
  }
}

/**
 * Update existing cuisine badge with new cuisine name
 *
 * @param {HTMLElement} badgeElement - The badge element to update
 * @param {string} newCuisineName - New cuisine name
 * @param {Object} options - Update options
 */
export function updateCuisineBadge(badgeElement, newCuisineName, options = {}) {
  // Input validation
  if (!badgeElement || !(badgeElement instanceof HTMLElement)) {
    console.warn('Invalid badge element provided for update');
    return;
  }

  if (!newCuisineName || typeof newCuisineName !== 'string') {
    console.warn('Invalid cuisine name provided for update');
    return;
  }

  // Update data attribute
  badgeElement.dataset.cuisine = newCuisineName;

  // Re-enhance the badge
  enhanceCuisineBadge(badgeElement, options);
}

/**
 * Get cuisine color as CSS custom property value
 * Useful for dynamic styling
 *
 * @param {string} cuisineName - Name of the cuisine
 * @returns {string} CSS custom property declaration
 */
export function getCuisineColorProperty(cuisineName) {
  const color = getCuisineColor(cuisineName);
  return `--cuisine-color: ${color}`;
}

// Auto-initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
  console.log('Auto-initializing cuisine badges...');
  initializeCuisineBadges();
});

// Re-initialize when content is dynamically added
export function reinitializeCuisineBadges() {
  initializeCuisineBadges('.cuisine-badge:not(.cuisine-enhanced)');
}

// Export for global access
window.CuisineBadge = {
  initialize: initializeCuisineBadges,
  enhance: enhanceCuisineBadge,
  create: createCuisineBadgeElement,
  update: updateCuisineBadge,
  reinitialize: reinitializeCuisineBadges,
  getColorProperty: getCuisineColorProperty,
};
