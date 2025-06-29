/**
 * Module Loader
 * Dynamically loads and initializes page-specific JavaScript modules based on data attributes
 */

// Cache of loaded modules to prevent multiple initializations
const loadedModules = new Set();

// Base URL for static files
const staticBaseUrl = window.staticBaseUrl || '';

/**
 * Load and initialize a module
 * @param {string} moduleName - Name of the module to load
 * @param {HTMLElement} element - The element that triggered the module load
 */
function loadModule(moduleName, element) {
    try {
        // Skip if already loaded
        if (loadedModules.has(moduleName)) {
            console.log(`Module ${moduleName} already loaded, skipping`);
            return Promise.resolve();
        }

        console.log(`Loading module: ${moduleName}`);

        // Create a script element to load the module
        return new Promise((resolve, reject) => {
            const script = document.createElement('script');
            script.type = 'module';
            script.src = `${staticBaseUrl}/static/js/pages/${moduleName}.js`;
            script.onload = () => {
                // The module should handle its own initialization
                loadedModules.add(moduleName);
                console.log(`Loaded module: ${moduleName}`);
                resolve();
            };
            script.onerror = (error) => {
                console.error(`Error loading module ${moduleName}:`, error);
                reject(error);
            };
            document.head.appendChild(script);
        });
    } catch (error) {
        console.error(`Error with module ${moduleName}:`, error);
        return Promise.reject(error);
    }
}

/**
 * Initialize modules based on data attributes
 */
function initModules() {
    // Find all elements with data-module attribute
    const moduleElements = document.querySelectorAll('[data-module]');

    moduleElements.forEach(element => {
        const moduleName = element.getAttribute('data-module');
        if (moduleName) {
            // Add a data attribute to mark this element as initialized
            element.setAttribute('data-module-initialized', 'true');
            loadModule(moduleName, element).catch(console.error);
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
