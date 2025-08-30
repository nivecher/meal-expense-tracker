/**
 * Enhanced Sticky Table Component
 * Provides improved functionality for sticky headers and frozen columns
 *
 * Features:
 * - Dynamic header height calculation
 * - Smooth scrolling behavior
 * - Resize handling
 * - Mobile optimization
 * - Performance optimizations
 *
 * Usage:
 * StickyTable.init(); // Initialize all sticky tables on page
 * StickyTable.initTable(element); // Initialize specific table
 */

class StickyTable {
  constructor(container) {
    this.container = container;
    this.table = container.querySelector('table');
    this.headers = container.querySelectorAll('thead th');
    this.isSticky = container.classList.contains('table-sticky-header') ||
                       container.classList.contains('table-sticky-frozen');
    this.isFrozen = container.classList.contains('table-frozen-columns') ||
                       container.classList.contains('table-sticky-frozen');

    this.init();
  }

  init() {
    if (!this.table) return;

    this.setupHeaders();
    this.setupScrollHandlers();
    this.setupResizeHandler();
    this.addMobileOptimizations();

    // Performance optimization: Use passive listeners for scroll events
    this.setupPassiveScrolling();
  }

  setupHeaders() {
    if (!this.isSticky) return;

    // Calculate and set proper header heights
    this.headers.forEach((header) => {
      const computedStyle = window.getComputedStyle(header);
      const height = header.offsetHeight;
      header.style.minHeight = `${height}px`;
    });
  }

  setupScrollHandlers() {
    if (!this.container) return;

    let scrollTimeout;

    this.container.addEventListener('scroll', () => {
      // Debounce scroll events for better performance
      clearTimeout(scrollTimeout);
      scrollTimeout = setTimeout(() => {
        this.handleScroll();
      }, 16); // ~60fps
    }, { passive: true });
  }

  handleScroll() {
    const { scrollTop } = this.container;
    const { scrollLeft } = this.container;

    // Add shadow effect when scrolling
    if (this.isSticky) {
      this.updateStickyHeaderShadow(scrollTop);
    }

    if (this.isFrozen) {
      this.updateFrozenColumnShadow(scrollLeft);
    }
  }

  updateStickyHeaderShadow(scrollTop) {
    const headers = this.container.querySelectorAll('thead th');
    const shadowIntensity = Math.min(scrollTop / 20, 1);

    headers.forEach((header) => {
      header.style.boxShadow = `0 2px ${4 + shadowIntensity * 8}px rgba(0, 0, 0, ${0.1 + shadowIntensity * 0.1})`;
    });
  }

  updateFrozenColumnShadow(scrollLeft) {
    const firstColumnCells = this.container.querySelectorAll('th:first-child, td:first-child');
    const shadowIntensity = Math.min(scrollLeft / 20, 1);

    firstColumnCells.forEach((cell) => {
      cell.style.boxShadow = `2px 0 ${4 + shadowIntensity * 8}px rgba(0, 0, 0, ${0.1 + shadowIntensity * 0.1})`;
    });
  }

  setupResizeHandler() {
    let resizeTimeout;

    window.addEventListener('resize', () => {
      clearTimeout(resizeTimeout);
      resizeTimeout = setTimeout(() => {
        this.handleResize();
      }, 250);
    });
  }

  handleResize() {
    // Recalculate header heights on resize
    this.setupHeaders();

    // Update mobile optimizations
    this.addMobileOptimizations();
  }

  addMobileOptimizations() {
    const isMobile = window.innerWidth < 768;

    if (isMobile) {
      // Reduce header padding on mobile
      this.headers.forEach((header) => {
        header.style.padding = '0.5rem 0.25rem';
      });

      // Adjust container height
      if (this.isSticky) {
        this.container.style.maxHeight = '60vh';
      }
    } else {
      // Reset to default padding
      this.headers.forEach((header) => {
        header.style.padding = '';
      });

      if (this.isSticky) {
        this.container.style.maxHeight = '70vh';
      }
    }
  }

  setupPassiveScrolling() {
    // Use transform3d to trigger hardware acceleration
    if (this.table) {
      this.table.style.transform = 'translate3d(0, 0, 0)';
    }
  }

  // Static methods for easy initialization
  static init() {
    // Initialize all sticky tables on the page
    const stickyContainers = document.querySelectorAll(
      '.table-sticky-header, .table-frozen-columns, .table-sticky-frozen',
    );

    stickyContainers.forEach((container) => {
      new StickyTable(container);
    });
  }

  static initTable(element) {
    return new StickyTable(element);
  }

  // Utility methods
  static addStickyClasses(tableContainer, type = 'header') {
    const validTypes = ['header', 'frozen', 'both'];
    if (!validTypes.includes(type)) {
      console.warn('Invalid sticky table type. Use: header, frozen, or both');
      return;
    }

    // Remove existing sticky classes
    tableContainer.classList.remove('table-responsive', 'table-sticky-header', 'table-frozen-columns', 'table-sticky-frozen');

    // Add appropriate class
    switch (type) {
      case 'header':
        tableContainer.classList.add('table-sticky-header');
        break;
      case 'frozen':
        tableContainer.classList.add('table-frozen-columns');
        break;
      case 'both':
        tableContainer.classList.add('table-sticky-frozen');
        break;
    }

    // Initialize the sticky functionality
    StickyTable.initTable(tableContainer);
  }
}

// Auto-initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
  StickyTable.init();
});

// Also initialize on dynamic content load (for AJAX loaded tables)
document.addEventListener('htmx:afterSettle', () => {
  StickyTable.init();
});

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
  module.exports = StickyTable;
}

// Global access
window.StickyTable = StickyTable;
