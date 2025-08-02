/**
 * UI Demo JavaScript
 * Handles interactive elements on the UI demo page
 */

document.addEventListener('DOMContentLoaded', () => {
  // Initialize tooltips
  const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
  tooltipTriggerList.map((tooltipTriggerEl) => {
    return new bootstrap.Tooltip(tooltipTriggerEl);
  });

  // Initialize popovers
  const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
  popoverTriggerList.map((popoverTriggerEl) => {
    return new bootstrap.Popover(popoverTriggerEl);
  });

  // Initialize alert close buttons
  const alertCloseButtons = document.querySelectorAll('.alert .btn-close');
  alertCloseButtons.forEach((button) => {
    button.addEventListener('click', function () {
      const alert = this.closest('.alert');
      if (alert) {
        alert.classList.remove('show');
        setTimeout(() => alert.remove(), 150);
      }
    });
  });

  // Handle loading state demo buttons
  const loadingButtons = document.querySelectorAll('.btn-loading-demo');
  loadingButtons.forEach((button) => {
    button.addEventListener('click', (e) => {
      e.preventDefault();
      const btn = e.currentTarget;
      const originalText = btn.innerHTML;
      const loadingText = btn.getAttribute('data-loading-text') || 'Loading...';

      // Show loading state
      btn.disabled = true;
      btn.innerHTML = `
                <span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>
                ${loadingText}
            `;

      // Simulate loading
      setTimeout(() => {
        btn.disabled = false;
        btn.innerHTML = originalText;

        // Show success message
        const alert = document.createElement('div');
        alert.className = 'alert alert-success mt-3';
        alert.role = 'alert';
        alert.innerHTML = `
                    <i class="bi bi-check-circle-fill me-2"></i>
                    Action completed successfully!
                `;

        const container = btn.closest('.component-card') || btn.closest('.card-body') || document.body;
        container.appendChild(alert);

        // Remove alert after 3 seconds
        setTimeout(() => {
          alert.classList.add('fade');
          setTimeout(() => alert.remove(), 150);
        }, 3000);
      }, 2000);
    });
  });

  // Handle tab switching for component demos
  const demoNavLinks = document.querySelectorAll('[data-bs-toggle="tab"]');
  demoNavLinks.forEach((link) => {
    link.addEventListener('shown.bs.tab', (e) => {
      const target = document.querySelector(e.target.dataset.bsTarget);
      // Trigger resize event for any charts or components that need it
      window.dispatchEvent(new Event('resize'));
    });
  });

  // Initialize clipboard for code examples
  const copyButtons = document.querySelectorAll('.btn-copy');
  copyButtons.forEach((button) => {
    button.addEventListener('click', function () {
      const codeBlock = this.closest('pre');
      const code = codeBlock.querySelector('code').innerText;

      navigator.clipboard.writeText(code).then(() => {
        // Show tooltip feedback
        const tooltip = bootstrap.Tooltip.getInstance(button);
        const originalTitle = button.getAttribute('data-bs-original-title');

        button.setAttribute('data-bs-original-title', 'Copied!');
        tooltip.show();

        setTimeout(() => {
          button.setAttribute('data-bs-original-title', originalTitle);
          tooltip.hide();
        }, 2000);
      });
    });
  });

  // Handle form submission in the demo
  const demoForm = document.getElementById('demoForm');
  if (demoForm) {
    demoForm.addEventListener('submit', (e) => {
      e.preventDefault();

      // Get form data
      const formData = new FormData(demoForm);
      const formObject = {};
      formData.forEach((value, key) => {
        formObject[key] = value;
      });

      // Show success message
      const alert = document.createElement('div');
      alert.className = 'alert alert-success mt-3';
      alert.role = 'alert';
      alert.innerHTML = `
                <i class="bi bi-check-circle-fill me-2"></i>
                Form submitted successfully! <pre class="d-none d-md-inline ms-2 mb-0">${JSON.stringify(formObject, null, 2)}</pre>
            `;

      const formContainer = demoForm.closest('.component-card') || demoForm;
      formContainer.appendChild(alert);

      // Reset form
      demoForm.reset();

      // Scroll to show the message
      alert.scrollIntoView({ behavior: 'smooth' });

      // Remove alert after 5 seconds
      setTimeout(() => {
        alert.classList.add('fade');
        setTimeout(() => alert.remove(), 150);
      }, 5000);
    });
  }
});
