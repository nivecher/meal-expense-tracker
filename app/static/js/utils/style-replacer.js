/**
 * Style Replacer Utility
 * Dynamically replaces inline styles with CSS classes
 *
 * @version 1.0.0
 * @author Meal Expense Tracker Team
 */

export class StyleReplacer {
    constructor(options = {}) {
        this.enabled = options.enabled !== false; // Default to enabled
        this.verbose = options.verbose || false; // Default to quiet
        this.styleMappings = {
            // Layout and sizing
            'min-width: 80px': 'amount-min-width',
            'width: auto; min-width: 80px': 'per-page-select',
            'word-break: break-all': 'word-break-all',

            // Restaurant icons
            'display: none; font-size: 24px': 'restaurant-fallback-icon',
            'display: none; font-size: 14px': 'restaurant-fallback-icon-table',
            'display: none; font-size: 28px': 'restaurant-fallback-icon-large',
            'opacity: 0; transition: opacity 0.2s': 'restaurant-icon-opacity',
            'opacity: 0; transition: opacity 0.2s; margin-top: 2px': 'restaurant-icon-opacity-with-margin',

            // Scrollable containers
            'max-height: 200px; overflow-y: auto': 'scrollable-container-sm',
            'max-height: 300px; overflow-y: auto': 'scrollable-container-md',
            'max-height: 400px; overflow-y: auto': 'scrollable-container-lg',

            // Table columns
            'min-width: 100px': 'table-col-100',
            'min-width: 120px': 'table-col-120',
            'min-width: 150px': 'table-col-150',
            'min-width: 200px': 'table-col-200',

            // Avatar styles
            'display: none; width: 32px; height: 32px': 'avatar-initials avatar-initials-sm',
            'display: none; width: 36px; height: 36px': 'avatar-initials avatar-initials-md',

            // Button states
            'display: none': 'btn-hidden',

            // Icon sizes
            'font-size: 2rem': 'icon-size-2rem'
        };
    }

    init() {
        if (!this.enabled) {
            return;
        }

        // Only run once after a short delay to let dynamic content load
        setTimeout(() => {
            this.replaceInlineStyles();
            this.setupDynamicStyles();
        }, 1000);
    }

    replaceInlineStyles() {
        // Find all elements with inline styles
        const elementsWithStyles = document.querySelectorAll('[style]');

        elementsWithStyles.forEach(element => {
            // Skip elements that are dynamically created by JavaScript
            if (this.shouldSkipElement(element)) {
                return;
            }

            const style = element.getAttribute('style');
            const className = this.getMatchingClass(style);

            if (className) {
                // Remove inline style and add class
                element.removeAttribute('style');
                element.classList.add(...className.split(' '));

                // Only log in development mode and if verbose is enabled
                if (this.verbose && (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1')) {
                    console.log(`Style replacer: Replaced "${style.substring(0, 50)}..." with class "${className}"`);
                }
            }
        });
    }

    shouldSkipElement(element) {
        // Skip elements that are part of JavaScript components
        const skipSelectors = [
            '.restaurant-suggestions', // Restaurant autocomplete dropdown
            '.tagify__dropdown', // Tagify dropdown
            '.select2-dropdown', // Select2 dropdown
            '[data-dynamic]', // Elements marked as dynamic
            '.dropdown-menu', // Bootstrap dropdowns
            '.tooltip', // Bootstrap tooltips
            '.popover' // Bootstrap popovers
        ];

        // Check if element matches any skip selector
        for (const selector of skipSelectors) {
            if (element.matches(selector) || element.closest(selector)) {
                return true;
            }
        }

        // Skip elements created in the last 2 seconds (likely dynamic)
        const createdTime = element.dataset.createdTime;
        if (createdTime && (Date.now() - parseInt(createdTime)) < 2000) {
            return true;
        }

        return false;
    }

    getMatchingClass(style) {
        // Normalize style string
        const normalizedStyle = style.replace(/\s+/g, ' ').trim();

        // Check for exact matches
        for (const [stylePattern, className] of Object.entries(this.styleMappings)) {
            if (normalizedStyle.includes(stylePattern)) {
                return className;
            }
        }

        return null;
    }

    setupDynamicStyles() {
        // Handle dynamic color styles
        this.setupDynamicColors();
        this.setupProgressBars();
    }

    setupDynamicColors() {
        // Replace cuisine color styles
        document.querySelectorAll('[style*="--cuisine-color"]').forEach(element => {
            const style = element.getAttribute('style');
            const colorMatch = style.match(/--cuisine-color:\s*([^;]+)/);
            const rgbMatch = style.match(/--cuisine-color-rgb:\s*([^;]+)/);

            if (colorMatch) {
                element.classList.add('cuisine-badge');
                element.style.setProperty('--default-cuisine-color', colorMatch[1].trim());
                if (rgbMatch) {
                    element.style.setProperty('--default-cuisine-color-rgb', rgbMatch[1].trim());
                }
                element.removeAttribute('style');
            }
        });

        // Replace category color styles
        document.querySelectorAll('[style*="--category-color"]').forEach(element => {
            const style = element.getAttribute('style');
            const colorMatch = style.match(/--category-color:\s*([^;]+)/);
            const rgbMatch = style.match(/--category-color-rgb:\s*([^;]+)/);

            if (colorMatch) {
                element.classList.add('category-badge');
                element.style.setProperty('--default-category-color', colorMatch[1].trim());
                if (rgbMatch) {
                    element.style.setProperty('--default-category-color-rgb', rgbMatch[1].trim());
                }
                element.removeAttribute('style');
            }
        });

        // Replace tag color styles
        document.querySelectorAll('[style*="background-color"]').forEach(element => {
            const style = element.getAttribute('style');
            const colorMatch = style.match(/background-color:\s*([^;]+)/);

            if (colorMatch && element.classList.contains('tag-badge')) {
                element.classList.add('tag-badge-custom');
                element.style.setProperty('--tag-color', colorMatch[1].trim());
                element.removeAttribute('style');
            }
        });
    }

    setupProgressBars() {
        // Replace progress bar width styles
        document.querySelectorAll('[style*="--progress-width"]').forEach(element => {
            const style = element.getAttribute('style');
            const widthMatch = style.match(/--progress-width:\s*([^;]+)/);

            if (widthMatch) {
                element.classList.add('progress-bar-dynamic');
                element.style.setProperty('--progress-width', widthMatch[1].trim());
                element.removeAttribute('style');
            }
        });
    }

    // Utility method to apply styles to new elements
    applyStylesToElement(element, styleType, value) {
        switch (styleType) {
            case 'cuisine-color':
                element.classList.add('cuisine-badge');
                element.style.setProperty('--default-cuisine-color', value);
                break;
            case 'category-color':
                element.classList.add('category-badge');
                element.style.setProperty('--default-category-color', value);
                break;
            case 'tag-color':
                element.classList.add('tag-badge-custom');
                element.style.setProperty('--tag-color', value);
                break;
            case 'progress-width':
                element.classList.add('progress-bar-dynamic');
                element.style.setProperty('--progress-width', value);
                break;
        }
    }

    // Public methods to control behavior
    enable() {
        this.enabled = true;
    }

    disable() {
        this.enabled = false;
    }

    setVerbose(verbose) {
        this.verbose = verbose;
    }
}

// Initialize when DOM is ready - DISABLED BY DEFAULT
// Uncomment the line below to enable automatic style replacement
// document.addEventListener('DOMContentLoaded', () => {
//     new StyleReplacer({ enabled: true, verbose: false });
// });
