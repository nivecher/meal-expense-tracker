/**
 * Help Page
 * 
 * Handles auto-expand functionality and enhanced navigation for accordion sections.
 * This replaces the inline JavaScript in the main/help.html template.
 */

document.addEventListener('DOMContentLoaded', () => {
  // Auto-expand sections based on URL hash
  if (window.location.hash) {
    const targetId = window.location.hash.substring(1);
    const targetElement = document.getElementById(targetId);
    if (targetElement && targetElement.classList.contains('accordion-item')) {
      const collapseElement = targetElement.querySelector('.accordion-collapse');
      if (collapseElement) {
        new bootstrap.Collapse(collapseElement, { show: true });
      }
    }
  }

  // Enhanced navigation for accordion sections
  document.querySelectorAll('a[href^="#"]').forEach((anchor) => {
    anchor.addEventListener('click', function(e) {
      e.preventDefault();
      const targetId = this.getAttribute('href').substring(1);
      const targetElement = document.getElementById(targetId);

      if (targetElement && targetElement.classList.contains('accordion-item')) {
        // Find the collapse element within this accordion item
        const collapseElement = targetElement.querySelector('.accordion-collapse');
        if (collapseElement) {
          // Check if the section is already open
          if (collapseElement.classList.contains('show')) {
            // Already open, just scroll to it
            targetElement.scrollIntoView({
              behavior: 'smooth',
              block: 'start',
            });
          } else {
            // Open the accordion section using Bootstrap's Collapse API
            new bootstrap.Collapse(collapseElement, { show: true });

            // Wait for the collapse animation to complete, then scroll
            collapseElement.addEventListener(
              'shown.bs.collapse',
              () => {
                targetElement.scrollIntoView({
                  behavior: 'smooth',
                  block: 'start',
                });
              },
              { once: true },
            );
          }
        }
      } else if (targetElement) {
        // Regular smooth scrolling for non-accordion targets
        targetElement.scrollIntoView({
          behavior: 'smooth',
          block: 'start',
        });
      }
    });
  });
});
