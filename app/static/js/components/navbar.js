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

    this.setupDropdowns();
    this.setupResizeObserver();
    this.setupMobileMenuToggle();
    this.setupKeyboardNavigation();
    this.setupAccessibility();
    this.updateResponsiveState();
  }

  setupDropdowns() {
    // Find all dropdown toggles
    this.dropdownToggles = this.navbar.querySelectorAll('[data-bs-toggle="dropdown"], .dropdown-toggle');

    this.dropdownToggles.forEach((toggle) => {
      toggle.addEventListener('click', (e) => {
        e.preventDefault();
        this.handleDropdownToggle(toggle);
      });

      // Close dropdown when clicking outside
      document.addEventListener('click', (e) => {
        if (!toggle.contains(e.target) && !toggle.nextElementSibling?.contains(e.target)) {
          this.closeDropdown(toggle);
        }
      });
    });
  }

  handleDropdownToggle(toggle) {
    const isOpen = toggle.getAttribute('aria-expanded') === 'true';

    // Close all other dropdowns first
    this.dropdownToggles.forEach((otherToggle) => {
      if (otherToggle !== toggle) {
        this.closeDropdown(otherToggle);
      }
    });

    if (isOpen) {
      this.closeDropdown(toggle);
    } else {
      this.openDropdown(toggle);
    }
  }

  openDropdown(toggle) {
    const dropdown = toggle.nextElementSibling;
    if (!dropdown) return;

    toggle.setAttribute('aria-expanded', 'true');
    dropdown.classList.add('show');

    // Add animation class
    dropdown.style.animation = 'dropdownFadeIn 0.2s ease-out';

    // Position dropdown correctly
    this.positionDropdown(dropdown, toggle);
  }

  closeDropdown(toggle) {
    const dropdown = toggle.nextElementSibling;
    if (!dropdown) return;

    toggle.setAttribute('aria-expanded', 'false');
    dropdown.classList.remove('show');
    dropdown.style.animation = '';
  }

  positionDropdown(dropdown, toggle) {
    const rect = toggle.getBoundingClientRect();
    const dropdownRect = dropdown.getBoundingClientRect();
    const viewportWidth = window.innerWidth;

    // Check if dropdown would overflow on the right
    if (rect.left + dropdownRect.width > viewportWidth - 20) {
      dropdown.style.left = 'auto';
      dropdown.style.right = '0';
    } else {
      dropdown.style.left = '0';
      dropdown.style.right = 'auto';
    }
  }

  setupResizeObserver() {
    const resizeObserver = new ResizeObserver((entries) => {
      const { width } = entries[0].contentRect;
      const wasMobile = this.isMobile;
      const wasTablet = this.isTablet;
      const wasSmallMobile = this.isSmallMobile;

      this.isMobile = width < this.breakpoints.mobile;
      this.isTablet = width < this.breakpoints.tablet;
      this.isSmallMobile = width < this.breakpoints.smallMobile;

      // Reset mobile menu state when switching between mobile and desktop
      if (wasMobile !== this.isMobile) {
        if (!this.isMobile) {
          // Reset all dropdowns when switching to desktop
          this.dropdownToggles.forEach((toggle) => {
            this.closeDropdown(toggle);
          });
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

  setupKeyboardNavigation() {
    // Handle keyboard navigation for dropdowns
    this.dropdownToggles.forEach((toggle) => {
      toggle.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          this.handleDropdownToggle(toggle);
        } else if (e.key === 'Escape') {
          this.closeDropdown(toggle);
        }
      });
    });

    // Handle keyboard navigation for mobile menu
    if (this.navbarToggler) {
      this.navbarToggler.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          // Mobile menu toggle functionality removed - using icon-only navigation
        }
      });
    }
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
    skipLink.className = 'skip-link sr-only sr-only-focusable';
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
    this.setupDropdowns();
    this.updateResponsiveState();
  }

  destroy() {
    // Clean up event listeners
    this.dropdownToggles.forEach((toggle) => {
      toggle.removeEventListener('click', this.handleDropdownToggle);
    });

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
