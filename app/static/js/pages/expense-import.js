/**
 * Expense Import Page
 *
 * Handles form validation for expense CSV import functionality.
 * This replaces the inline JavaScript in the expenses/import.html template.
 */

function setProgressUiVisible(isVisible) {
  const container = document.getElementById('import-upload-progress');
  if (!container) {
    return;
  }

  container.classList.toggle('d-none', !isVisible);
}

function setProgressUiState({ percent, statusText, isAnimated }) {
  const bar = document.getElementById('import-upload-bar');
  const percentEl = document.getElementById('import-upload-percent');
  const statusEl = document.getElementById('import-upload-status');

  if (!bar || !percentEl || !statusEl) {
    return;
  }

  const clampedPercent = Math.max(0, Math.min(100, percent));
  bar.style.width = `${clampedPercent}%`;
  bar.setAttribute('aria-valuenow', String(clampedPercent));
  percentEl.textContent = `${clampedPercent}%`;
  statusEl.textContent = statusText;

  bar.classList.toggle('progress-bar-animated', isAnimated);
  bar.classList.toggle('progress-bar-striped', isAnimated);
}

function clearErrorUi() {
  const errorEl = document.getElementById('import-upload-error');
  if (!errorEl) {
    return;
  }

  errorEl.textContent = '';
  errorEl.classList.add('d-none');
}

function setFormDisabled(form, isDisabled) {
  const buttons = form.querySelectorAll('button, input[type="submit"]');
  buttons.forEach((btn) => {
    btn.disabled = isDisabled;
  });
}

document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('import-form');
  if (!form) {
    return;
  }

  const fileInput = form.querySelector('#file');
  if (!fileInput) {
    return;
  }

  // Reset any initial validation states
  fileInput.classList.remove('is-invalid', 'is-valid');

  form.addEventListener('submit', (event) => {
    // Clear any previous validation states
    fileInput.classList.remove('is-invalid', 'is-valid');
    clearErrorUi();

    if (!fileInput.files.length) {
      event.preventDefault();
      event.stopPropagation();
      fileInput.classList.add('is-invalid');
      form.classList.add('was-validated');
      return;
    }

    fileInput.classList.add('is-valid');
    setFormDisabled(form, true);
    setProgressUiVisible(true);
    setProgressUiState({
      percent: 100,
      statusText: 'Processing import…',
      isAnimated: true,
    });
  });

  fileInput.addEventListener('change', function onFileChange() {
    // Clear any validation classes when file selection changes
    this.classList.remove('is-invalid', 'is-valid');
    clearErrorUi();
    setProgressUiVisible(false);

    if (this.files.length) {
      // File selected, show positive feedback but don't persist it
      this.classList.add('is-valid');

      // Remove validation state after a short delay to prevent persistent green border
      setTimeout(() => {
        if (!form.classList.contains('was-validated')) {
          this.classList.remove('is-valid');
        }
      }, 1000);
    }
  });

  // Clear validation states when form is reset or page loads
  form.addEventListener('reset', () => {
    fileInput.classList.remove('is-invalid', 'is-valid');
    form.classList.remove('was-validated');
    clearErrorUi();
    setProgressUiVisible(false);
    setFormDisabled(form, false);
  });
});
