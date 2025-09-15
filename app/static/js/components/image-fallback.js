/**
 * Simple image fallback component for handling failed image loads
 * CSP-compliant solution that avoids external API calls
 * Optimized to reduce forced reflows and improve performance
 */

export function initImageFallback() {
    // Batch DOM updates to reduce reflows
    let pendingUpdates = new Map();

    function batchUpdate(element, updates) {
        if (!pendingUpdates.has(element)) {
            pendingUpdates.set(element, {});
        }
        Object.assign(pendingUpdates.get(element), updates);
    }

    function flushUpdates() {
        pendingUpdates.forEach((updates, element) => {
            Object.assign(element.style, updates);
        });
        pendingUpdates.clear();
    }

    // Handle favicon fallbacks with optimized DOM updates
    document.addEventListener('error', (event) => {
        if (event.target.tagName === 'IMG' &&
            (event.target.classList.contains('restaurant-favicon') ||
             event.target.classList.contains('restaurant-favicon-table'))) {

            batchUpdate(event.target, { display: 'none' });

            const fallback = event.target.nextElementSibling;
            if (fallback &&
                (fallback.classList.contains('restaurant-fallback-icon') ||
                 fallback.classList.contains('restaurant-fallback-icon-table') ||
                 fallback.classList.contains('restaurant-fallback-icon-large'))) {
                batchUpdate(fallback, {
                    display: 'inline-block',
                });
            }

            // Flush updates on next tick to batch DOM changes
            requestAnimationFrame(flushUpdates);
        }
    }, true);

    // Handle successful image loads with opacity transition
    document.addEventListener('load', (event) => {
        if (event.target.tagName === 'IMG' &&
            (event.target.classList.contains('restaurant-favicon') ||
             event.target.classList.contains('restaurant-favicon-table'))) {

            batchUpdate(event.target, { opacity: '1' });
            requestAnimationFrame(flushUpdates);
        }
    }, true);

    // Handle avatar fallbacks
    document.addEventListener('error', (event) => {
        if (event.target.tagName === 'IMG' && event.target.classList.contains('avatar-img')) {
            batchUpdate(event.target, { display: 'none' });

            const fallback = event.target.nextElementSibling;
            if (fallback && fallback.classList.contains('avatar-fallback')) {
                batchUpdate(fallback, { display: 'flex' });
            }

            requestAnimationFrame(flushUpdates);
        }
    }, true);
}

// Auto-initialize when module loads
initImageFallback();
