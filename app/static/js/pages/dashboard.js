/**
 * Dashboard page functionality
 * Handles dashboard-specific interactions and enhancements
 */

class Dashboard {
  constructor() {
    this.init();
  }

  init() {
    this.setupStatsAnimation();
    this.setupQuickActions();
    this.setupResponsiveFeatures();
  }

  /**
     * Animate stats cards on page load
     */
  setupStatsAnimation() {
    const statsCards = document.querySelectorAll('.stats-card');

    // Intersection Observer for scroll animations
    const observer = new IntersectionObserver((entries) => {
      entries.forEach((entry, index) => {
        if (entry.isIntersecting) {
          setTimeout(() => {
            entry.target.style.animation = 'fadeInUp 0.6s ease forwards';
          }, index * 100);
        }
      });
    }, { threshold: 0.1 });

    statsCards.forEach((card) => {
      card.style.opacity = '0';
      card.style.transform = 'translateY(20px)';
      observer.observe(card);
    });
  }

  /**
     * Enhanced quick action buttons
     */
  setupQuickActions() {
    const quickActionBtns = document.querySelectorAll('.quick-action-btn');

    quickActionBtns.forEach((btn) => {
      // Add ripple effect on click
      btn.addEventListener('click', (e) => {
        this.createRippleEffect(e, btn);
      });

      // Add keyboard navigation
      btn.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          btn.click();
        }
      });
    });
  }

  /**
     * Responsive feature enhancements
     */
  setupResponsiveFeatures() {
    // Handle mobile-specific interactions
    if (this.isMobile()) {
      this.setupMobileOptimizations();
    }

    // Handle window resize
    window.addEventListener('resize', () => {
      this.handleResize();
    });
  }

  /**
     * Mobile-specific optimizations
     */
  setupMobileOptimizations() {
    // Touch-friendly hover effects
    const hoverElements = document.querySelectorAll('.expense-item, .restaurant-item');

    hoverElements.forEach((element) => {
      element.addEventListener('touchstart', () => {
        element.classList.add('touch-active');
      });

      element.addEventListener('touchend', () => {
        setTimeout(() => {
          element.classList.remove('touch-active');
        }, 150);
      });
    });
  }

  /**
     * Handle window resize events
     */
  handleResize() {
    // Adjust layout for different screen sizes
    const welcomeSection = document.querySelector('.welcome-section');
    if (welcomeSection) {
      if (window.innerWidth < 768) {
        welcomeSection.classList.add('mobile-layout');
      } else {
        welcomeSection.classList.remove('mobile-layout');
      }
    }
  }

  /**
     * Create ripple effect for button clicks
     */
  createRippleEffect(event, element) {
    const ripple = document.createElement('span');
    const rect = element.getBoundingClientRect();
    const size = Math.max(rect.width, rect.height);

    ripple.style.width = `${size}px`;
    ripple.style.height = `${size}px`;
    ripple.style.left = `${event.clientX - rect.left - size / 2}px`;
    ripple.style.top = `${event.clientY - rect.top - size / 2}px`;
    ripple.classList.add('ripple-effect');

    element.appendChild(ripple);

    setTimeout(() => {
      ripple.remove();
    }, 600);
  }

  /**
     * Check if device is mobile
     */
  isMobile() {
    return window.innerWidth <= 768 || /Android|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
  }

  /**
     * Format currency values
     */
  static formatCurrency(amount) {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
    }).format(amount);
  }

  /**
     * Format date values
     */
  static formatDate(dateString) {
    const date = new Date(dateString);
    return new Intl.DateTimeFormat('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    }).format(date);
  }
}

// Additional CSS for animations and effects
const style = document.createElement('style');
style.textContent = `
    @keyframes fadeInUp {
        from {
            opacity: 0;
            transform: translateY(20px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }

    .touch-active {
        background-color: #f8f9fa !important;
        transform: scale(0.98);
        transition: all 0.1s ease;
    }

    .ripple-effect {
        position: absolute;
        border-radius: 50%;
        background: rgba(13, 110, 253, 0.3);
        transform: scale(0);
        animation: ripple 0.6s linear;
        pointer-events: none;
    }

    @keyframes ripple {
        to {
            transform: scale(4);
            opacity: 0;
        }
    }

    .quick-action-btn {
        position: relative;
        overflow: hidden;
    }

    .mobile-layout .welcome-content h1 {
        font-size: 1.75rem !important;
    }

    .mobile-layout .lead {
        font-size: 0.95rem !important;
    }
`;
document.head.appendChild(style);

// Initialize dashboard when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
  new Dashboard();
});

// Export for potential use in other modules
export default Dashboard;
