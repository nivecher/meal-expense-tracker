/**
 * Cuisine type formatting utilities for Google Places data
 * Provides consistent formatting for cuisine types across the application
 * Following TIGER principles: Safety, Performance, Developer Experience
 */

/**
 * Cuisine constants with colors and icons for consistent display
 * Each cuisine has name, color (hex), icon (Font Awesome), and description
 */
const CUISINE_CONSTANTS = [
  { name: 'Chinese', color: '#dc2626', icon: 'utensils', description: 'Chinese cuisine' },
  { name: 'Italian', color: '#16a34a', icon: 'pizza-slice', description: 'Italian cuisine' },
  { name: 'Japanese', color: '#e91e63', icon: 'fish', description: 'Japanese cuisine' },
  { name: 'Mexican', color: '#ea580c', icon: 'pepper-hot', description: 'Mexican cuisine' },
  { name: 'Indian', color: '#f59e0b', icon: 'fire', description: 'Indian cuisine' },
  { name: 'Thai', color: '#059669', icon: 'leaf', description: 'Thai cuisine' },
  { name: 'French', color: '#7c3aed', icon: 'wine-glass', description: 'French cuisine' },
  { name: 'American', color: '#2563eb', icon: 'utensils', description: 'American cuisine' },
  { name: 'Barbecue', color: '#7c2d12', icon: 'drumstick-bite', description: 'Barbecue cuisine' },
  { name: 'Pizza', color: '#16a34a', icon: 'pizza-slice', description: 'Pizza restaurants' },
  { name: 'Seafood', color: '#0891b2', icon: 'fish', description: 'Seafood restaurants' },
  { name: 'Steakhouse', color: '#7c2d12', icon: 'drumstick-bite', description: 'Steakhouse restaurants' },
  { name: 'Sushi', color: '#e91e63', icon: 'fish', description: 'Sushi restaurants' },
  { name: 'Korean', color: '#dc2626', icon: 'fire', description: 'Korean cuisine' },
  { name: 'Vietnamese', color: '#059669', icon: 'utensils', description: 'Vietnamese cuisine' },
  { name: 'Mediterranean', color: '#0891b2', icon: 'leaf', description: 'Mediterranean cuisine' },
  { name: 'Greek', color: '#2563eb', icon: 'leaf', description: 'Greek cuisine' },
  { name: 'Spanish', color: '#f59e0b', icon: 'pepper-hot', description: 'Spanish cuisine' },
  { name: 'German', color: '#6b7280', icon: 'beer', description: 'German cuisine' },
  { name: 'British', color: '#7c3aed', icon: 'crown', description: 'British cuisine' },
  { name: 'Turkish', color: '#dc2626', icon: 'star', description: 'Turkish cuisine' },
  { name: 'Lebanese', color: '#16a34a', icon: 'leaf', description: 'Lebanese cuisine' },
  { name: 'Ethiopian', color: '#f59e0b', icon: 'fire', description: 'Ethiopian cuisine' },
  { name: 'Moroccan', color: '#ea580c', icon: 'star', description: 'Moroccan cuisine' },
  { name: 'Brazilian', color: '#16a34a', icon: 'leaf', description: 'Brazilian cuisine' },
  { name: 'Peruvian', color: '#dc2626', icon: 'pepper-hot', description: 'Peruvian cuisine' },
  { name: 'Argentinian', color: '#2563eb', icon: 'drumstick-bite', description: 'Argentinian cuisine' },
  { name: 'Fast Food', color: '#fbbf24', icon: 'burger', description: 'Fast food cuisine' },
];

/**
 * Map of Google Places restaurant types to formatted cuisine types
 * Key: Google Places type (lowercase)
 * Value: Formatted cuisine type (proper case)
 */
const CUISINE_TYPE_MAP = {
  chinese_restaurant: 'Chinese',
  italian_restaurant: 'Italian',
  japanese_restaurant: 'Japanese',
  mexican_restaurant: 'Mexican',
  indian_restaurant: 'Indian',
  thai_restaurant: 'Thai',
  french_restaurant: 'French',
  american_restaurant: 'American',
  barbecue_restaurant: 'Barbecue',
  pizza_restaurant: 'Pizza',
  seafood_restaurant: 'Seafood',
  steak_house: 'Steakhouse',
  sushi_restaurant: 'Sushi',
  korean_restaurant: 'Korean',
  vietnamese_restaurant: 'Vietnamese',
  mediterranean_restaurant: 'Mediterranean',
  greek_restaurant: 'Greek',
  spanish_restaurant: 'Spanish',
  german_restaurant: 'German',
  british_restaurant: 'British',
  turkish_restaurant: 'Turkish',
  lebanese_restaurant: 'Lebanese',
  ethiopian_restaurant: 'Ethiopian',
  moroccan_restaurant: 'Moroccan',
  brazilian_restaurant: 'Brazilian',
  peruvian_restaurant: 'Peruvian',
  argentinian_restaurant: 'Argentinian',
  fast_food_restaurant: 'Fast Food',
};

/**
 * Map of restaurant establishment types to formatted values
 * Key: Google Places type (lowercase)
 * Value: Formatted type (lowercase for consistency with existing form)
 */
const ESTABLISHMENT_TYPE_MAP = {
  bar: 'bar',
  night_club: 'bar',
  cafe: 'cafe',
  coffee_shop: 'cafe',
  bakery: 'bakery',
  meal_takeaway: 'fast_food',
  meal_delivery: 'fast_food',
  restaurant: 'restaurant',
  food: 'restaurant',
  establishment: 'restaurant',
};

/**
 * Format cuisine type from Google Places data with proper capitalization
 *
 * @param {string|undefined} cuisineType - Raw cuisine type from Google Places
 * @param {number} maxLength - Maximum length for cuisine string (default: 100)
 * @returns {string} Formatted cuisine type or empty string
 *
 * @example
 * formatCuisineType('mexican') // returns 'Mexican'
 * formatCuisineType('ITALIAN') // returns 'Italian'
 * formatCuisineType('chinese_restaurant') // returns 'Chinese'
 */
export function formatCuisineType(cuisineType, maxLength = 100) {
  // Input validation - safety first
  if (!cuisineType || typeof cuisineType !== 'string') {
    return '';
  }

  // Enforce bounds to prevent overflow
  const trimmedInput = cuisineType.trim();
  if (trimmedInput.length === 0 || trimmedInput.length > maxLength) {
    return '';
  }

  const lowerCaseType = trimmedInput.toLowerCase();

  // Check direct mapping first (most specific)
  if (CUISINE_TYPE_MAP.hasOwnProperty(lowerCaseType)) {
    return CUISINE_TYPE_MAP[lowerCaseType];
  }

  // Handle simple word capitalization for unmapped types
  return capitalizeWords(lowerCaseType);
}

/**
 * Extract and format cuisine type from Google Places types array
 *
 * @param {Array<string>} googlePlacesTypes - Array of Google Places types
 * @param {string|undefined} primaryType - Primary type from Google Places
 * @returns {string} Formatted cuisine type or empty string
 *
 * @example
 * extractCuisineFromTypes(['restaurant', 'mexican_restaurant']) // returns 'Mexican'
 * extractCuisineFromTypes(['establishment', 'food']) // returns ''
 */
export function extractCuisineFromTypes(googlePlacesTypes, primaryType) {
  // Input validation
  if (!Array.isArray(googlePlacesTypes)) {
    return '';
  }

  // Process array with bounds checking
  const maxTypesToProcess = 20; // Prevent excessive processing
  const typesToCheck = googlePlacesTypes.slice(0, maxTypesToProcess);

  // Check each type for cuisine mapping
  for (const type of typesToCheck) {
    if (typeof type === 'string') {
      const formattedCuisine = formatCuisineType(type);
      if (formattedCuisine && CUISINE_TYPE_MAP.hasOwnProperty(type.toLowerCase())) {
        return formattedCuisine;
      }
    }
  }

  // Check primary type as fallback
  if (primaryType && typeof primaryType === 'string') {
    const formattedPrimary = formatCuisineType(primaryType);
    if (formattedPrimary && CUISINE_TYPE_MAP.hasOwnProperty(primaryType.toLowerCase())) {
      return formattedPrimary;
    }
  }

  return '';
}

/**
 * Extract establishment type from Google Places types array
 *
 * @param {Array<string>} googlePlacesTypes - Array of Google Places types
 * @param {string|undefined} primaryType - Primary type from Google Places
 * @returns {string} Establishment type (restaurant, cafe, bar, bakery, other) or 'restaurant' as default
 *
 * @example
 * extractEstablishmentType(['cafe', 'establishment']) // returns 'cafe'
 * extractEstablishmentType(['bar', 'night_club']) // returns 'bar'
 */
export function extractEstablishmentType(googlePlacesTypes, primaryType) {
  // Input validation
  if (!Array.isArray(googlePlacesTypes)) {
    return 'restaurant'; // Safe default
  }

  // Process array with bounds checking
  const maxTypesToProcess = 20;
  const typesToCheck = googlePlacesTypes.slice(0, maxTypesToProcess);

  // Check each type for establishment mapping
  for (const type of typesToCheck) {
    if (typeof type === 'string') {
      const lowerType = type.toLowerCase();
      if (ESTABLISHMENT_TYPE_MAP.hasOwnProperty(lowerType)) {
        return ESTABLISHMENT_TYPE_MAP[lowerType];
      }
    }
  }

  // Check primary type as fallback
  if (primaryType && typeof primaryType === 'string') {
    const lowerPrimary = primaryType.toLowerCase();
    if (ESTABLISHMENT_TYPE_MAP.hasOwnProperty(lowerPrimary)) {
      return ESTABLISHMENT_TYPE_MAP[lowerPrimary];
    }

    // Handle primaryType containing keywords
    if (lowerPrimary.includes('restaurant')) {
      return 'restaurant';
    } else if (lowerPrimary.includes('cafe')) {
      return 'cafe';
    } else if (lowerPrimary.includes('bar')) {
      return 'bar';
    }
  }

  return 'restaurant'; // Safe default
}

/**
 * Map Google Places types to both establishment type and cuisine
 * Combines establishment and cuisine extraction in one function for efficiency
 *
 * @param {Array<string>} googlePlacesTypes - Array of Google Places types
 * @param {string|undefined} primaryType - Primary type from Google Places
 * @returns {Object} Object containing formatted type and cuisine
 *
 * @example
 * mapPlaceTypesToRestaurant(['restaurant', 'mexican_restaurant'])
 * // returns { type: 'restaurant', cuisine: 'Mexican' }
 */
export function mapPlaceTypesToRestaurant(googlePlacesTypes, primaryType) {
  // Input validation and bounds checking
  if (!Array.isArray(googlePlacesTypes)) {
    console.log('No types array provided for place type mapping');
    return { type: 'restaurant', cuisine: '' };
  }

  if (googlePlacesTypes.length > 50) { // Safety bounds
    console.warn('Excessive Google Places types array length, truncating');
  }

  console.log('Mapping place types:', googlePlacesTypes.slice(0, 10), 'Primary type:', primaryType);

  const result = {
    type: extractEstablishmentType(googlePlacesTypes, primaryType),
    cuisine: extractCuisineFromTypes(googlePlacesTypes, primaryType),
  };

  console.log('Mapped to type:', result.type, 'cuisine:', result.cuisine);
  return result;
}

/**
 * Capitalize first letter of each word in a string
 * Internal utility function for formatting unmapped cuisine types
 *
 * @param {string} str - String to capitalize
 * @returns {string} Capitalized string
 */
function capitalizeWords(str) {
  if (!str || typeof str !== 'string') {
    return '';
  }

  return str
    .split(/[\s_-]+/) // Split on whitespace, underscore, or dash
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
    .join(' ');
}

/**
 * Get cuisine data by name from constants
 *
 * @param {string} cuisineName - Name of the cuisine to look up
 * @returns {Object|null} Cuisine data object or null if not found
 *
 * @example
 * getCuisineData('Italian') // returns {name: 'Italian', color: '#198754', icon: 'pizza-slice', description: 'Italian cuisine'}
 */
export function getCuisineData(cuisineName) {
  // Input validation - safety first
  if (!cuisineName || typeof cuisineName !== 'string') {
    return null;
  }

  // Enforce bounds to prevent excessive processing
  if (cuisineName.length > 100) {
    return null;
  }

  // Case-insensitive lookup
  const normalizedName = cuisineName.trim();

  for (const cuisine of CUISINE_CONSTANTS) {
    if (cuisine.name.toLowerCase() === normalizedName.toLowerCase()) {
      return { ...cuisine }; // Return copy for safety
    }
  }

  return null;
}

/**
 * Get color for a cuisine type
 *
 * @param {string} cuisineName - Name of the cuisine
 * @returns {string} Hex color code or default gray if not found
 *
 * @example
 * getCuisineColor('Mexican') // returns '#fd7e14'
 * getCuisineColor('Unknown') // returns '#6c757d'
 */
export function getCuisineColor(cuisineName) {
  const cuisineData = getCuisineData(cuisineName);
  return cuisineData ? cuisineData.color : '#6c757d'; // Default gray
}

/**
 * Get icon for a cuisine type
 *
 * @param {string} cuisineName - Name of the cuisine
 * @returns {string} Font Awesome icon name or default question icon if not found
 *
 * @example
 * getCuisineIcon('Italian') // returns 'pizza-slice'
 * getCuisineIcon('Unknown') // returns 'question'
 */
export function getCuisineIcon(cuisineName) {
  const cuisineData = getCuisineData(cuisineName);
  return cuisineData ? cuisineData.icon : 'question'; // Default question
}

/**
 * Get all cuisine constants
 *
 * @returns {Array} Array of cuisine data objects
 *
 * @example
 * getCuisineConstants() // returns array of all cuisine objects
 */
export function getCuisineConstants() {
  return CUISINE_CONSTANTS.map(cuisine => ({ ...cuisine })); // Return copies for safety
}

/**
 * Create a cuisine badge HTML with color and icon
 *
 * @param {string} cuisineName - Name of the cuisine
 * @param {Object} options - Options for badge styling
 * @param {boolean} options.showIcon - Whether to show icon (default: true)
 * @param {string} options.className - Additional CSS classes
 * @returns {string} HTML string for the cuisine badge
 *
 * @example
 * createCuisineBadge('Italian') // returns HTML badge with Italian styling
 */
export function createCuisineBadge(cuisineName, options = {}) {
  const { showIcon = true, className = '' } = options;

  // Input validation
  if (!cuisineName || typeof cuisineName !== 'string') {
    return '<span class="badge bg-light text-dark">-</span>';
  }

  const cuisineData = getCuisineData(cuisineName);
  if (!cuisineData) {
    return `<span class="badge bg-light text-dark ${className}">${cuisineName}</span>`;
  }

  const iconHtml = showIcon && cuisineData.icon
    ? `<i class="fas fa-${cuisineData.icon} me-1"></i>`
    : '';

  return `<span class="badge border d-flex align-items-center ${className}"
                style="background-color: ${cuisineData.color}20;
                       color: ${cuisineData.color};
                       border-color: ${cuisineData.color}40 !important">
            ${iconHtml}${cuisineData.name}
          </span>`;
}

/**
 * Validate if a cuisine name exists in our constants
 *
 * @param {string} cuisineName - Name to validate
 * @returns {boolean} True if cuisine exists, false otherwise
 *
 * @example
 * validateCuisineName('Chinese') // returns true
 * validateCuisineName('Unknown') // returns false
 */
export function validateCuisineName(cuisineName) {
  return getCuisineData(cuisineName) !== null;
}

/**
 * Validate and sanitize cuisine input for storage
 * Used when users manually enter cuisine types
 *
 * @param {string} userInput - User-provided cuisine string
 * @param {number} maxLength - Maximum allowed length (default: 100)
 * @returns {string} Sanitized and formatted cuisine string
 *
 * @example
 * sanitizeCuisineInput('  mexican  ') // returns 'Mexican'
 * sanitizeCuisineInput('FAST-FOOD') // returns 'Fast Food'
 */
export function sanitizeCuisineInput(userInput, maxLength = 100) {
  // Input validation
  if (!userInput || typeof userInput !== 'string') {
    return '';
  }

  // Sanitize and enforce bounds
  const trimmed = userInput.trim();
  if (trimmed.length === 0 || trimmed.length > maxLength) {
    return '';
  }

  // Remove any potentially harmful characters (basic sanitization)
  const cleaned = trimmed.replace(/[<>\"'&]/g, '');

  // Format consistently
  return capitalizeWords(cleaned);
}
