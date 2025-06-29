/**
 * Main application entry point
 * Handles dynamic imports and module initialization.
 */

// Import necessary utilities
import { loadGoogleMapsAPI } from './services/google-maps.service.js';

// Page modules map - maps URL paths to their corresponding module paths
const PAGE_MODULES = {
    '/restaurants/add': '/static/js/pages/restaurant-form.js',
    '/restaurants/search': '/static/js/pages/restaurant-search.js',
    // Add more routes as needed
};

// Initialize the application
async function init() {
    try {
        // Initialize UI components
        initUI();

        // Load and initialize the current page module
        await loadPageModule();

    } catch (error) {
        console.error('Error initializing application:', error);
    }
}

// Initialize UI components
function initUI() {
    // Initialize tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Initialize popovers
    const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });

    // Add smooth scrolling for anchor links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth'
                });
            }
        });
    });

    // Add animation to cards on scroll
    const animateOnScroll = function() {
        const cards = document.querySelectorAll('.card, .animate-on-scroll');
        cards.forEach(card => {
            const cardTop = card.getBoundingClientRect().top;
            const windowHeight = window.innerHeight;

            if (cardTop < windowHeight - 100) {
                card.classList.add('animate__animated', 'animate__fadeInUp');
            }
        });
    };

    // Add scroll event listener
    window.addEventListener('scroll', animateOnScroll);
    animateOnScroll(); // Run once on page load

    // Add loading state to buttons with data-loading attribute
    document.querySelectorAll('[data-loading]').forEach(button => {
        button.addEventListener('click', function() {
            this.setAttribute('data-text', this.innerHTML);
            this.disabled = true;
            this.innerHTML = `
                <span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>
                ${this.getAttribute('data-loading')}
            `;
        });
    });
}

// Load and initialize the current page module
async function loadPageModule() {
    const currentPath = window.location.pathname;
    let modulePath = null;

    // Find the matching module path for the current route
    for (const [path, module] of Object.entries(PAGE_MODULES)) {
        if (currentPath.startsWith(path)) {
            modulePath = module;
            break;
        }
    }

    if (!modulePath) {
        console.log('No specific module found for path:', currentPath);
        return;
    }

    try {
        // Load the module
        const module = await import(modulePath);

        // Initialize the module if it has an init function
        if (typeof module.init === 'function') {
            console.log('Initializing module:', modulePath);
            await module.init();
        }

    } catch (error) {
        console.error(`Error loading module ${modulePath}:`, error);
    }
}

// Load Google Maps API if needed
async function loadGoogleMapsIfNeeded() {
    const needsGoogleMaps = document.querySelector('.needs-google-maps');
    if (needsGoogleMaps && !window.google) {
        try {
            await loadGoogleMapsAPI();
        } catch (error) {
            console.error('Failed to load Google Maps API:', error);
        }
    }
}

// Initialize the application when the DOM is fully loaded
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
} else {
    init();
}

// Flash message auto-dismiss
document.addEventListener('DOMContentLoaded', function() {
    const alerts = document.querySelectorAll('.alert-dismissible');
    alerts.forEach(alert => {
        setTimeout(() => {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 5000); // Auto-dismiss after 5 seconds
    });
});

// Export for testing
export {
    init,
    initUI,
    loadPageModule,
    loadGoogleMapsIfNeeded
};
