/**
 * Dependency Loader
 * Ensures all required dependencies are loaded before initializing the application
 */

/**
 * Check if a script is already loaded
 * @param {string} src - The script source URL to check
 * @returns {boolean} True if the script is already loaded
 */
function isScriptLoaded(src) {
    return Array.from(document.scripts).some(script => script.src === src);
}

/**
 * Load a script dynamically
 * @param {string} src - The script source URL
 * @param {string} [integrity] - Optional integrity hash
 * @param {string} [crossOrigin] - Optional cross-origin attribute
 * @returns {Promise<void>}
 */
function loadScript(src, integrity = '', crossOrigin = 'anonymous') {
    return new Promise((resolve, reject) => {
        // Check if script is already loaded
        if (isScriptLoaded(src)) {
            console.log(`Script already loaded: ${src}`);
            resolve();
            return;
        }

        const script = document.createElement('script');
        script.src = src;
        script.async = true;
        script.defer = true;

        if (integrity) {
            script.integrity = integrity;
            script.crossOrigin = crossOrigin || 'anonymous';
        }

        script.onload = () => {
            console.log(`Script loaded: ${src}`);
            resolve();
        };

        script.onerror = (error) => {
            console.error(`Error loading script: ${src}`, error);
            reject(new Error(`Failed to load script: ${src}`));
        };

        document.head.appendChild(script);
    });
}

/**
 * Load all required dependencies
 * @returns {Promise<void>}
 */
async function loadDependencies() {
    const dependencies = [
        // jQuery
        {
            src: 'https://code.jquery.com/jquery-3.7.1.min.js',
            integrity: 'sha256-/JqT3SQfawRcv/BIHPThkBvs0OEvtFFmqPF/lYI/Cxo=',
            crossOrigin: 'anonymous'
        },
        // Bootstrap Bundle with Popper
        {
            src: 'https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js',
            integrity: 'sha384-geWF76RCwLtnZ8qwWowPQNguL3RmwHVBC9FhGdlKrxdiJJigb/j/68SIy3Te4Bkz',
            crossOrigin: 'anonymous'
        },
        // Select2
        {
            src: 'https://cdn.jsdelivr.net/npm/select2@4.1.0-rc.0/dist/js/select2.min.js'
        }
    ];

    try {
        // Load all dependencies in parallel
        await Promise.all(dependencies.map(dep =>
            loadScript(dep.src, dep.integrity, dep.crossOrigin)
        ));

        // Verify Bootstrap is available
        if (typeof bootstrap === 'undefined') {
            throw new Error('Bootstrap not loaded');
        }

        // Verify jQuery is available
        if (typeof jQuery === 'undefined') {
            throw new Error('jQuery not loaded');
        }

        // Verify Select2 is available
        if (typeof jQuery.fn.select2 === 'undefined') {
            throw new Error('Select2 not loaded');
        }

        console.log('All dependencies loaded successfully');
        return true;
    } catch (error) {
        console.error('Error loading dependencies:', error);
        throw error;
    }
}

export { loadDependencies, loadScript };
