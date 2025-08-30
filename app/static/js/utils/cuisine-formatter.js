/**
 * Cuisine type formatting utilities for Google Places data
 * Provides consistent formatting for cuisine types across the application
 * Following TIGER principles: Safety, Performance, Developer Experience
 */

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
