/**
 * Form handling and validation utilities (legacy entry point)
 * @deprecated Use /static/js/utils/forms/index.js instead
 * @module FormUtils
 */

// Import the new implementation
import FormUtils from './forms/index.js';

// Export for CommonJS/legacy usage
if (typeof module !== 'undefined' && module.exports) {
  module.exports = FormUtils;
}

// Set up global FormUtils if not already defined
if (typeof window !== 'undefined' && !window.formsInitialized) {
  window.formsInitialized = true;
  window.FormUtils = FormUtils;
}
