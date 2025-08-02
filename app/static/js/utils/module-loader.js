/**
 * Module Loader
 * Dynamically loads and initializes page-specific JavaScript modules based on data attributes
 */

import { logger } from './logger.js';

// Cache of loaded modules to prevent multiple initializations
const loadedModules = new Set();

// Base URL for static files
const staticBaseUrl = window.staticBaseUrl || '';

/**
 * Load and initialize a module
 * @param {string} moduleName - Name of the module to load
 * @param {HTMLElement} [_element] - The element that triggered the module load (optional)
 */
function loadModule (moduleName, _element) {
  try {
    // Skip if already loaded
    if (loadedModules.has(moduleName)) {
      logger.debug(`Module ${moduleName} already loaded, skipping`);
      return Promise.resolve();
    }

    logger.debug(`Loading module: ${moduleName}`);

    // Create a script element to load the module
    return new Promise((resolve, reject) => {
      const script = document.createElement('script');
      script.type = 'module';
      script.src = `${staticBaseUrl}/static/js/pages/${moduleName}.js`;
      script.onload = () => {
        // The module should handle its own initialization
        loadedModules.add(moduleName);
        logger.info(`Loaded module: ${moduleName}`);
        resolve();
      };
      script.onerror = (error) => {
        logger.error(`Failed to load module ${moduleName}:`, error);
        reject(error);
      };
      document.head.appendChild(script);
    });
  } catch (error) {
    logger.error(`Error with module ${moduleName}:`, error);
    return Promise.reject(error);
  }
}

/**
 * Check if a module's required elements are present
 * @param {string} moduleName - Name of the module to check
 * @returns {boolean} True if all required elements are present
 */
function shouldLoadModule (moduleName) {
  switch(moduleName) {
    case 'restaurant-search':
      // Only load if the search form and map container exist
      return document.getElementById('restaurant-search-form') &&
                   document.getElementById('map');
      // Add other module conditions here
    default:
      return true; // Default to loading if we don't have specific conditions
  }
}

/**
 * Initialize all modules found in the document
 */
function initModules () {
  console.log('Initializing modules...');

  // Find all elements with data-module attribute
  const moduleElements = document.querySelectorAll('[data-module]');

  // Load each module if its required elements are present
  moduleElements.forEach((element) => {
    const moduleName = element.dataset.module;
    if (moduleName && shouldLoadModule(moduleName)) {
      // Add a data attribute to mark this element as initialized
      element.setAttribute('data-module-initialized', 'true');
      loadModule(moduleName, element).catch(console.error);
    } else if (moduleName) {
      console.log(`Skipping module ${moduleName} - required elements not found`);
    }
  });
}

// Initialize modules when DOM is loaded
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initModules);
} else {
  // DOMContentLoaded has already fired
  initModules();
}

export { loadModule, initModules };
