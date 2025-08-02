/**
 * Navbar functionality
 * Handles mobile menu toggle and dropdown interactions
 */
class NavbarManager {
  constructor () {
    this.navbar = document.querySelector('.navbar');
    this.navbarToggler = this.navbar?.querySelector('.navbar-toggler');
    this.navbarCollapse = this.navbar?.querySelector('.navbar-collapse');
    this.dropdownToggles = [];
    this.isMobile = window.innerWidth < 992; // Bootstrap's lg breakpoint

    this.init();
  }

  init () {
    document.addEventListener('DOMContentLoaded', () => {
      this.setupEventListeners();
      this.setupDropdowns();
      this.setupResizeObserver();
    });
  }

  setupEventListeners () {
    // Mobile menu toggle
    if (this.navbarToggler && this.navbarCollapse) {
      this.navbarToggler.addEventListener('click', (e) => {
        e.preventDefault();
        this.toggleMobileMenu();
      });
    }

    // Close mobile menu when clicking outside
    document.addEventListener('click', (e) => {
      if (this.isMobileMenuOpen() &&
                !this.navbar.contains(e.target) &&
                !e.target.closest('.navbar')) {
        this.closeMobileMenu();
      }
    });

    // Handle escape key
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && this.isMobileMenuOpen()) {
        this.closeMobileMenu();
      }
    });
  }

  setupDropdowns () {
    // Find all dropdown toggles in the navbar
    this.dropdownToggles = Array.from(
      this.navbar?.querySelectorAll('.dropdown-toggle') || [],
    );

    this.dropdownToggles.forEach((toggle) => {
      // Handle click on dropdown toggles
      toggle.addEventListener('click', (e) => {
        if (this.isMobile) {
          e.preventDefault();
          e.stopPropagation();
          this.toggleDropdown(toggle);
        }
      });

      // Add aria-expanded if not present
      if (!toggle.hasAttribute('aria-expanded')) {
        toggle.setAttribute('aria-expanded', 'false');
      }
    });
  }

  setupResizeObserver () {
    // Handle responsive behavior
    const resizeObserver = new ResizeObserver((entries) => {
      const { width } = entries[0].contentRect;
      const wasMobile = this.isMobile;
      this.isMobile = width < 992;

      // Reset mobile menu state when switching between mobile and desktop
      if (wasMobile !== this.isMobile) {
        if (!this.isMobile) {
          this.closeMobileMenu();
          // Reset all dropdowns
          this.dropdownToggles.forEach((toggle) => {
            this.closeDropdown(toggle);
          });
        }
      }
    });

    if (this.navbar) {
      resizeObserver.observe(this.navbar);
    }
  }

  toggleMobileMenu () {
    if (this.navbarCollapse.classList.contains('show')) {
      this.closeMobileMenu();
    } else {
      this.openMobileMenu();
    }
  }

  openMobileMenu () {
    if (!this.navbarCollapse) return;

    this.navbarCollapse.classList.add('show');
    this.navbarToggler.setAttribute('aria-expanded', 'true');

    // Add a class to body to prevent scrolling when menu is open
    document.body.classList.add('mobile-menu-open');

    // Dispatch custom event
    this.navbar.dispatchEvent(new CustomEvent('mobileMenuOpened'));
  }

  closeMobileMenu () {
    if (!this.navbarCollapse) return;

    this.navbarCollapse.classList.remove('show');
    this.navbarToggler.setAttribute('aria-expanded', 'false');

    // Remove the class that prevents scrolling
    document.body.classList.remove('mobile-menu-open');

    // Close all dropdowns when closing mobile menu
    this.dropdownToggles.forEach((toggle) => {
      this.closeDropdown(toggle);
    });

    // Dispatch custom event
    this.navbar.dispatchEvent(new CustomEvent('mobileMenuClosed'));
  }

  isMobileMenuOpen () {
    return this.navbarCollapse?.classList.contains('show');
  }

  toggleDropdown (toggle) {
    const isExpanded = toggle.getAttribute('aria-expanded') === 'true';

    // Close all other dropdowns first
    this.dropdownToggles.forEach((t) => {
      if (t !== toggle) {
        this.closeDropdown(t);
      }
    });

    // Toggle the clicked dropdown
    if (isExpanded) {
      this.closeDropdown(toggle);
    } else {
      this.openDropdown(toggle);
    }
  }

  openDropdown (toggle) {
    const dropdownMenu = toggle.nextElementSibling;
    if (!dropdownMenu || !dropdownMenu.classList.contains('dropdown-menu')) return;

    toggle.setAttribute('aria-expanded', 'true');
    dropdownMenu.classList.add('show');

    // Dispatch custom event
    this.navbar.dispatchEvent(new CustomEvent('dropdownOpened', {
      detail: { toggle, menu: dropdownMenu },
    }));
  }

  closeDropdown (toggle) {
    const dropdownMenu = toggle?.nextElementSibling;
    if (!dropdownMenu || !dropdownMenu.classList.contains('dropdown-menu')) return;

    toggle.setAttribute('aria-expanded', 'false');
    dropdownMenu.classList.remove('show');

    // Dispatch custom event
    this.navbar.dispatchEvent(new CustomEvent('dropdownClosed', {
      detail: { toggle, menu: dropdownMenu },
    }));
  }
}

// Initialize the navbar manager when the DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
  if (document.querySelector('.navbar')) {
    window.navbarManager = new NavbarManager();
  }
});
