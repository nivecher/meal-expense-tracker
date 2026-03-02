import { escapeHtml } from '../utils/security-utils.js';

class MerchantAutocomplete {
  constructor(inputElement) {
    this.input = inputElement;
    this.select = document.querySelector(this.input.dataset.merchantSelect || '#merchant_id');
    this.suggestionsContainer = null;
    this.selectedMerchant = null;
    this.debounceTimer = null;
    this.quickAddModal = document.getElementById('merchantQuickAddModal');
    this.quickAddSubmit = document.getElementById('quick_add_merchant_submit');
    this.quickAddName = document.getElementById('quick_add_merchant_name');
    this.quickAddShortName = document.getElementById('quick_add_merchant_short_name');
    this.quickAddWebsite = document.getElementById('quick_add_merchant_website');
    this.quickAddError = document.getElementById('quick_add_merchant_error');
    this.init();
  }

  init() {
    if (!this.input || !this.select) return;
    this.createSuggestionsContainer();
    this.setupEventListeners();
  }

  createSuggestionsContainer() {
    this.suggestionsContainer = document.createElement('div');
    this.suggestionsContainer.className = 'search-suggestions merchant-suggestions';
    this.suggestionsContainer.style.cssText = `
      position: absolute;
      top: 100%;
      left: 0;
      right: 0;
      background: white;
      border: 1px solid #ddd;
      border-top: none;
      border-radius: 0 0 4px 4px;
      box-shadow: 0 2px 4px rgba(0,0,0,0.1);
      max-height: 220px;
      overflow-y: auto;
      z-index: 1000;
      display: none;
    `;

    this.input.parentNode.style.position = 'relative';
    this.input.parentNode.appendChild(this.suggestionsContainer);
  }

  setupEventListeners() {
    this.input.addEventListener('focus', () => {
      if (!this.input.value.trim()) {
        this.handleInput('');
      }
    });

    this.input.addEventListener('input', (event) => {
      const value = event.target.value || '';
      if (this.selectedMerchant && value.trim() !== this.selectedMerchant.name) {
        this.clearSelection();
      }
      clearTimeout(this.debounceTimer);
      this.debounceTimer = setTimeout(() => this.handleInput(value), 400);
    });

    document.addEventListener('click', (event) => {
      if (!this.input.contains(event.target) && !this.suggestionsContainer.contains(event.target)) {
        this.hideSuggestions();
      }
    });

    if (this.quickAddSubmit) {
      this.quickAddSubmit.addEventListener('click', () => this.submitQuickAdd());
    }
  }

  clearSelection() {
    this.selectedMerchant = null;
    if (this.select) {
      this.select.value = '';
    }
  }

  async handleInput(query) {
    const trimmed = query.trim();
    if (trimmed.length === 0) {
      this.clearSelection();
      const suggestions = await this.fetchSuggestions('');
      this.renderSuggestions(suggestions, trimmed);
      return;
    }

    try {
      const suggestions = await this.fetchSuggestions(trimmed);
      this.renderSuggestions(suggestions, trimmed);
    } catch (error) {
      this.showError(error.message || 'Unable to load merchants');
    }
  }

  async fetchSuggestions(query) {
    const params = new URLSearchParams({ q: query });
    const response = await fetch(`/restaurants/merchants/api/list?${params.toString()}`, {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
    });

    if (!response.ok) {
      throw new Error(`Failed to fetch merchants (${response.status})`);
    }

    const data = await response.json();
    return Array.isArray(data) ? data : [];
  }

  renderSuggestions(suggestions, query) {
    this.suggestionsContainer.innerHTML = '';

    if (!suggestions.length) {
      const noResults = document.createElement('div');
      noResults.className = 'suggestion-item';
      const helperText = query ? `Add "${escapeHtml(query)}" as a new merchant` : 'No merchants available yet';
      noResults.innerHTML = `
        <div class="d-flex align-items-center p-2 text-muted">
          <i class="fas fa-search me-2"></i>
          <div class="flex-grow-1">
            <div class="fw-medium">No merchants found</div>
            <small class="text-muted">${helperText}</small>
          </div>
        </div>
      `;
      if (query) {
        noResults.addEventListener('click', () => this.openQuickAdd(query));
      }
      this.suggestionsContainer.appendChild(noResults);
      this.showSuggestions();
      return;
    }

    suggestions.forEach((merchant) => {
      const item = document.createElement('div');
      item.className = 'suggestion-item';
      const shortName = merchant.short_name
        ? ` <small class="text-muted">(${escapeHtml(merchant.short_name)})</small>`
        : '';
      item.innerHTML = `
        <div class="d-flex align-items-center p-2">
          <i class="fas fa-building text-primary me-2"></i>
          <div class="flex-grow-1">
            <div class="fw-medium">${escapeHtml(merchant.name)}${shortName}</div>
          </div>
        </div>
      `;
      item.addEventListener('click', () => this.selectMerchant(merchant));
      this.suggestionsContainer.appendChild(item);
    });

    this.showSuggestions();
  }

  showSuggestions() {
    this.suggestionsContainer.style.display = 'block';
  }

  hideSuggestions() {
    this.suggestionsContainer.style.display = 'none';
  }

  showError(message) {
    this.suggestionsContainer.innerHTML = `
      <div class="p-2 text-danger small">
        <i class="fas fa-exclamation-triangle me-1"></i>${escapeHtml(message)}
      </div>
    `;
    this.showSuggestions();
    setTimeout(() => this.hideSuggestions(), 2500);
  }

  selectMerchant(merchant) {
    this.selectedMerchant = merchant;
    this.input.value = merchant.name;
    this.ensureSelectOption(merchant);
    this.select.value = String(merchant.id);
    this.hideSuggestions();
  }

  ensureSelectOption(merchant) {
    if (!this.select) return;
    const exists = Array.from(this.select.options).some((opt) => opt.value === String(merchant.id));
    if (!exists) {
      const option = document.createElement('option');
      option.value = String(merchant.id);
      option.textContent = merchant.name;
      this.select.appendChild(option);
    }
  }

  openQuickAdd(name) {
    if (!this.quickAddModal) return;
    if (this.quickAddName) this.quickAddName.value = name || '';
    if (this.quickAddShortName) this.quickAddShortName.value = '';
    if (this.quickAddWebsite) this.quickAddWebsite.value = '';
    if (this.quickAddError) this.quickAddError.classList.add('d-none');
    const modal = new bootstrap.Modal(this.quickAddModal);
    modal.show();
  }

  async submitQuickAdd() {
    if (!this.quickAddName || !this.quickAddSubmit) return;
    const name = this.quickAddName.value.trim();
    const shortName = this.quickAddShortName ? this.quickAddShortName.value.trim() : '';
    const website = this.quickAddWebsite ? this.quickAddWebsite.value.trim() : '';

    if (!name) {
      this.showQuickAddError('Merchant name is required.');
      return;
    }

    this.quickAddSubmit.disabled = true;
    this.quickAddSubmit.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Saving...';

    try {
      const csrfToken =
        document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') ||
        document.querySelector('input[name="csrf_token"]')?.value ||
        '';
      const response = await fetch('/restaurants/merchants/api/quick-add', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': csrfToken,
          'X-Requested-With': 'XMLHttpRequest',
        },
        credentials: 'include',
        body: JSON.stringify({ name, short_name: shortName, website }),
      });

      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(data.message || 'Unable to add merchant');
      }

      const { merchant } = data;
      if (merchant) {
        this.selectMerchant(merchant);
      }

      const modal = bootstrap.Modal.getInstance(this.quickAddModal);
      if (modal) modal.hide();
    } catch (error) {
      this.showQuickAddError(error.message || 'Unable to add merchant');
    } finally {
      this.quickAddSubmit.disabled = false;
      this.quickAddSubmit.innerHTML = '<i class="fas fa-save me-2"></i>Add Merchant';
    }
  }

  showQuickAddError(message) {
    if (!this.quickAddError) return;
    this.quickAddError.textContent = message;
    this.quickAddError.classList.remove('d-none');
  }
}

function initMerchantAutocomplete() {
  const inputs = document.querySelectorAll('[data-merchant-autocomplete]');
  inputs.forEach((input) => {
    new MerchantAutocomplete(input); // eslint-disable-line no-new
  });
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initMerchantAutocomplete);
} else {
  initMerchantAutocomplete();
}

window.MerchantAutocomplete = MerchantAutocomplete;
