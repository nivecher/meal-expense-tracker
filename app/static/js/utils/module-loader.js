/**
 * Simple Module Loader
 * Loads modules based on data attributes without over-engineering
 */

// Track loaded modules
const loadedModules = new Set();

// Load a module if not already loaded
async function loadModule(moduleName) {
  if (loadedModules.has(moduleName)) return;

  try {
    const module = await import(`/static/js/pages/${moduleName}.js`);
    loadedModules.add(moduleName);
    module.init?.();
  } catch {
    console.error(`Failed to load module ${moduleName}:`, error);
  }
}

// Check if a module should be loaded
function shouldLoadModule(moduleName) {
  switch (moduleName) {
    case 'restaurant-search':
      return document.getElementById('restaurant-search-form') && document.getElementById('map');
    default:
      return true;
  }
}

// Initialize all modules found in the document
function initModules() {
  document.querySelectorAll('[data-module]').forEach((element) => {
    const moduleName = element.dataset.module;
    if (moduleName && shouldLoadModule(moduleName)) {
      element.setAttribute('data-module-initialized', 'true');
      loadModule(moduleName);
    }
  });
}

// Auto-initialize
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initModules);
} else {
  initModules();
}

export { loadModule, initModules };
