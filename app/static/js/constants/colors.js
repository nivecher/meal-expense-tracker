/**
 * Centralized Color Constants for Meal Expense Tracker Frontend
 * Following TIGER principles: Safety, Performance, Developer Experience
 *
 * This module provides a single source of truth for all colors used throughout
 * the frontend JavaScript, ensuring consistency with the backend constants.
 */

// Bootstrap 5 compatible color palette (must match app/constants/colors.py)
export const BOOTSTRAP_COLORS = {
  orange: {
    hex: '#fd7e14',
    name: 'Orange',
    description: 'Bootstrap orange - warm, energetic'
  },
  green: {
    hex: '#198754',
    name: 'Green',
    description: 'Bootstrap success green - fresh, positive'
  },
  cyan: {
    hex: '#0dcaf0',
    name: 'Cyan',
    description: 'Bootstrap info cyan - cool, refreshing'
  },
  red: {
    hex: '#dc3545',
    name: 'Red',
    description: 'Bootstrap danger red - attention, urgency'
  },
  purple: {
    hex: '#6f42c1',
    name: 'Purple',
    description: 'Bootstrap purple - creative, premium'
  },
  blue: {
    hex: '#0d6efd',
    name: 'Blue',
    description: 'Bootstrap primary blue - trustworthy, professional'
  },
  gray: {
    hex: '#6c757d',
    name: 'Gray',
    description: 'Bootstrap secondary gray - neutral, balanced'
  },
  yellow: {
    hex: '#ffc107',
    name: 'Yellow',
    description: 'Bootstrap warning yellow - caution, attention'
  },
  teal: {
    hex: '#20c997',
    name: 'Teal',
    description: 'Bootstrap teal - calm, natural'
  },
  indigo: {
    hex: '#6610f2',
    name: 'Indigo',
    description: 'Bootstrap indigo - deep, sophisticated'
  }
};

// Category-specific color mapping (must match app/constants/colors.py)
export const CATEGORY_COLORS = {
  restaurants: BOOTSTRAP_COLORS.orange.hex,      // #fd7e14
  groceries: BOOTSTRAP_COLORS.green.hex,         // #198754
  drinks: BOOTSTRAP_COLORS.cyan.hex,             // #0dcaf0
  fast_food: BOOTSTRAP_COLORS.red.hex,           // #dc3545
  entertainment: BOOTSTRAP_COLORS.purple.hex,    // #6f42c1
  snacks_vending: BOOTSTRAP_COLORS.blue.hex,     // #0d6efd
  other: BOOTSTRAP_COLORS.gray.hex,              // #6c757d
};

/**
 * Get hex color value with validation and fallback.
 *
 * @param {string} colorKey - Bootstrap color key (e.g., 'orange', 'green')
 * @returns {string} Hex color string with fallback to gray
 *
 * Following TIGER principles:
 * - Safety: Input validation with fallback
 * - Performance: Simple object lookup
 * - Developer Experience: Clear parameter names and documentation
 */
export function getColorHex(colorKey) {
  if (!colorKey || typeof colorKey !== 'string') {
    return BOOTSTRAP_COLORS.gray.hex;
  }

  const normalizedKey = colorKey.toLowerCase().trim();

  if (!BOOTSTRAP_COLORS[normalizedKey]) {
    return BOOTSTRAP_COLORS.gray.hex; // Default fallback
  }

  return BOOTSTRAP_COLORS[normalizedKey].hex;
}

/**
 * Get category color with validation and fallback.
 *
 * @param {string} categoryKey - Category key (e.g., 'restaurants', 'groceries')
 * @returns {string} Hex color string with fallback to gray
 */
export function getCategoryColor(categoryKey) {
  if (!categoryKey || typeof categoryKey !== 'string') {
    return BOOTSTRAP_COLORS.gray.hex;
  }

  const normalizedKey = categoryKey.toLowerCase().trim().replace(/\s+/g, '_').replace('&', '');

  if (!CATEGORY_COLORS[normalizedKey]) {
    return BOOTSTRAP_COLORS.gray.hex; // Default fallback
  }

  return CATEGORY_COLORS[normalizedKey];
}

/**
 * Convert hex color to RGB values for CSS custom properties.
 *
 * @param {string} hexColor - Hex color string (e.g., '#fd7e14')
 * @returns {string} RGB values string (e.g., '253, 126, 20')
 */
export function hexToRgb(hexColor) {
  if (!hexColor || typeof hexColor !== 'string' || !hexColor.startsWith('#') || hexColor.length !== 7) {
    return '108, 117, 125'; // Gray RGB fallback
  }

  const r = parseInt(hexColor.slice(1, 3), 16);
  const g = parseInt(hexColor.slice(3, 5), 16);
  const b = parseInt(hexColor.slice(5, 7), 16);

  return `${r}, ${g}, ${b}`;
}

/**
 * Get default gray color for fallbacks and unknown categories.
 *
 * @returns {string} Default gray hex color
 */
export function getDefaultGray() {
  return BOOTSTRAP_COLORS.gray.hex;
}

/**
 * Get default gray color with alpha for backgrounds.
 *
 * @param {number} alpha - Alpha value between 0 and 1
 * @returns {string} RGBA color string
 */
export function getDefaultGrayWithAlpha(alpha = 0.1) {
  const grayRgb = hexToRgb(BOOTSTRAP_COLORS.gray.hex);
  return `rgba(${grayRgb}, ${alpha})`;
}
