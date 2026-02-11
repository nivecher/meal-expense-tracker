/**
 * Responsive Navbar Manager
 * Handles mobile menu toggle, dropdown interactions, and responsive behavior
 * Provides smooth transitions between desktop and mobile layouts
 */
class ResponsiveNavbarManager {
  constructor() {
    this.navbar = document.querySelector('.navbar');
    this.navbarToggler = this.navbar?.querySelector('.navbar-toggler');
    this.navbarCollapse = this.navbar?.querySelector('.navbar-collapse');
    this.dropdownToggles = [];
    this.isMobile = window.innerWidth < 992; // Bootstrap's lg breakpoint
    this.isTablet = window.innerWidth < 1200;
    this.isSmallMobile = window.innerWidth < 576;

    // Responsive breakpoints
    this.breakpoints = {
      mobile: 992,
      tablet: 1200,
      smallMobile: 576,
    };

    this.init();
  }

  init() {
    if (!this.navbar) return;

    this.collectDropdownToggles();
    this.setupResizeObserver();
    this.setupMobileMenuToggle();
    this.setupAccessibility();
    this.updateResponsiveState();
  }

  collectDropdownToggles() {
    // Find all dropdown toggles for accessibility labeling
    this.dropdownToggles = this.navbar.querySelectorAll('[data-bs-toggle="dropdown"], .dropdown-toggle');
  }

  setupResizeObserver() {
    const resizeObserver = new ResizeObserver((entries) => {
      const { width } = entries[0].contentRect;
      const wasMobile = this.isMobile;
      // const wasTablet = this.isTablet; // Unused for now
      // const wasSmallMobile = this.isSmallMobile; // Unused for now

      this.isMobile = width < this.breakpoints.mobile;
      this.isTablet = width < this.breakpoints.tablet;
      this.isSmallMobile = width < this.breakpoints.smallMobile;

      // Reset mobile menu state when switching between mobile and desktop
      if (wasMobile !== this.isMobile) {
        if (!this.isMobile) {
          // Let Bootstrap manage dropdown state; nothing to reset here.
        }
      }

      // Update responsive state
      this.updateResponsiveState();
    });

    if (this.navbar) {
      resizeObserver.observe(this.navbar);
    }
  }

  setupMobileMenuToggle() {
    // Mobile menu toggle is no longer needed since we use icon-only navigation
    // This method is kept for compatibility but does nothing
  }

  setupAccessibility() {
    // Add ARIA labels and roles
    this.dropdownToggles.forEach((toggle) => {
      if (!toggle.getAttribute('aria-label')) {
        const text = toggle.textContent.trim() || toggle.getAttribute('title');
        toggle.setAttribute('aria-label', `${text} menu`);
      }
    });

    // Add skip link for keyboard navigation
    this.addSkipLink();
  }

  addSkipLink() {
    const skipLink = document.createElement('a');
    skipLink.href = '#main-content';
    skipLink.textContent = 'Skip to main content';
    skipLink.className = 'skip-link visually-hidden visually-hidden-focusable';
    skipLink.style.cssText = `
      position: absolute;
      top: -40px;
      left: 6px;
      z-index: 10000;
      color: white;
      background: var(--bs-primary);
      padding: 8px 16px;
      text-decoration: none;
      border-radius: 4px;
      transition: top 0.3s;
    `;

    skipLink.addEventListener('focus', () => {
      skipLink.style.top = '6px';
    });

    skipLink.addEventListener('blur', () => {
      skipLink.style.top = '-40px';
    });

    this.navbar.insertBefore(skipLink, this.navbar.firstChild);
  }

  updateResponsiveState() {
    // Add/remove classes based on screen size
    this.navbar.classList.toggle('is-mobile', this.isMobile);
    this.navbar.classList.toggle('is-tablet', this.isTablet);
    this.navbar.classList.toggle('is-small-mobile', this.isSmallMobile);

    // Update navbar height for mobile
    if (this.isMobile) {
      this.navbar.style.minHeight = '56px';
    } else {
      this.navbar.style.minHeight = '64px';
    }

    // Hide/show appropriate navigation elements
    this.updateNavigationVisibility();
  }

  updateNavigationVisibility() {
    const desktopNav = this.navbar.querySelector('.navbar-nav-desktop');
    const mobileNav = this.navbar.querySelector('.navbar-nav-mobile');

    if (this.isMobile) {
      // Mobile/tablet - show icon-only navigation
      if (desktopNav) desktopNav.style.display = 'none';
      if (mobileNav) mobileNav.style.display = 'flex';
    } else {
      // Desktop - show full navigation
      if (desktopNav) desktopNav.style.display = 'flex';
      if (mobileNav) mobileNav.style.display = 'none';
    }
  }

  // Public methods for external use
  refresh() {
    this.collectDropdownToggles();
    this.updateResponsiveState();
  }

  destroy() {
    // Mobile menu toggle functionality removed - no cleanup needed
  }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
  window.navbarManager = new ResponsiveNavbarManager();
});

// Handle page visibility changes
document.addEventListener('visibilitychange', () => {
  if (document.visibilityState === 'visible' && window.navbarManager) {
    window.navbarManager.refresh();
  }
});

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
  module.exports = ResponsiveNavbarManager;
}
