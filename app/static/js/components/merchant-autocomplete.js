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
    this.quickAddServiceLevel = document.getElementById('quick_add_merchant_service_level');
    this.quickAddCuisine = document.getElementById('quick_add_merchant_cuisine');
    this.quickAddMenuFocus = document.getElementById('quick_add_merchant_menu_focus');
    this.quickAddCategory = document.getElementById('quick_add_merchant_category');
    this.quickAddWebsite = document.getElementById('quick_add_merchant_website');
    this.quickAddError = document.getElementById('quick_add_merchant_error');
    this.summary = document.getElementById('merchant-association-summary');
    this.emptyState = document.getElementById('merchant-association-empty');
    this.summaryName = document.getElementById('merchant_summary_name');
    this.summaryMeta = document.getElementById('merchant_summary_meta');
    this.viewLink = document.getElementById('merchant_view_link');
    this.suggestionPanel = document.getElementById('merchant-suggestion-panel');
    this.suggestionName = document.getElementById('merchant_suggestion_name');
    this.suggestionMeta = document.getElementById('merchant_suggestion_meta');
    this.acceptSuggestionButton = document.getElementById('merchant_accept_suggestion');
    this.restaurantNameField = document.getElementById('name');
    this.suggestionDebounceTimer = null;
    this.suggestedMerchant = null;
    this.init();
  }

  init() {
    if (!this.input || !this.select) return;
    this.hydrateInitialSelection();
    this.createSuggestionsContainer();
    this.setupEventListeners();
    this.renderAssociationState();
    this.refreshSuggestion();
  }

  hydrateInitialSelection() {
    const { merchantId } = this.input.dataset;
    if (!merchantId) return;

    this.selectedMerchant = {
      id: merchantId,
      name: this.input.value.trim(),
      short_name: this.input.dataset.merchantShortName || '',
      service_level: this.input.dataset.merchantServiceLevel || '',
      cuisine: this.input.dataset.merchantCuisine || '',
      menu_focus: this.input.dataset.merchantMenuFocus || '',
      category: this.input.dataset.merchantCategory || '',
      website: this.input.dataset.merchantWebsite || '',
      is_chain: this.input.dataset.merchantIsChain === 'true',
      view_url: this.input.dataset.merchantViewUrl || '',
    };
    this.ensureSelectOption(this.selectedMerchant);
    this.select.value = String(merchantId);
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

    this.input.addEventListener('change', () => this.renderAssociationState());

    document.addEventListener('click', (event) => {
      if (!this.input.contains(event.target) && !this.suggestionsContainer.contains(event.target)) {
        this.hideSuggestions();
      }
    });

    if (this.quickAddSubmit) {
      this.quickAddSubmit.addEventListener('click', () => this.submitQuickAdd());
    }

    document.querySelectorAll('[data-merchant-action="open-create"]').forEach((button) => {
      button.addEventListener('click', () => this.openQuickAdd(this.restaurantNameField?.value || this.input.value));
    });

    document.querySelectorAll('[data-merchant-action="focus-search"]').forEach((button) => {
      button.addEventListener('click', () => {
        this.input.focus();
        this.handleInput(this.input.value || '');
      });
    });

    document.querySelectorAll('[data-merchant-action="clear-selection"]').forEach((button) => {
      button.addEventListener('click', () => this.clearSelection());
    });

    if (this.acceptSuggestionButton) {
      this.acceptSuggestionButton.addEventListener('click', () => {
        if (this.suggestedMerchant) {
          this.selectMerchant(this.suggestedMerchant);
        }
      });
    }

    if (this.restaurantNameField) {
      this.restaurantNameField.addEventListener('input', () => {
        clearTimeout(this.suggestionDebounceTimer);
        this.suggestionDebounceTimer = setTimeout(() => this.refreshSuggestion(), 350);
      });
      this.restaurantNameField.addEventListener('change', () => this.refreshSuggestion());
    }
  }

  clearSelection() {
    this.selectedMerchant = null;
    if (this.select) {
      this.select.value = '';
    }
    const aliasField = document.getElementById('merchant_alias');
    if (aliasField) {
      aliasField.value = '';
    }
    if (this.input) {
      delete this.input.dataset.merchantDisplayBase;
      delete this.input.dataset.merchantWebsite;
      delete this.input.dataset.merchantShortName;
      delete this.input.dataset.merchantServiceLevel;
      delete this.input.dataset.merchantCuisine;
      delete this.input.dataset.merchantMenuFocus;
      delete this.input.dataset.merchantCategory;
      delete this.input.dataset.merchantIsChain;
      delete this.input.dataset.merchantViewUrl;
      delete this.input.dataset.merchantId;
      this.input.value = '';
      this.input.dispatchEvent(new CustomEvent('merchant-cleared', { bubbles: true }));
    }
    this.renderAssociationState();
    this.refreshSuggestion();
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
    this.input.dataset.merchantDisplayBase = merchant.short_name || merchant.name || '';
    this.input.dataset.merchantWebsite = merchant.website || '';
    this.input.dataset.merchantShortName = merchant.short_name || '';
    this.input.dataset.merchantServiceLevel = merchant.service_level || '';
    this.input.dataset.merchantCuisine = merchant.cuisine || '';
    this.input.dataset.merchantMenuFocus = merchant.menu_focus || '';
    this.input.dataset.merchantCategory = merchant.category || '';
    this.input.dataset.merchantViewUrl = merchant.view_url || `/restaurants/merchants/${merchant.id}`;
    this.input.dataset.merchantIsChain = merchant.is_chain ? 'true' : 'false';
    this.input.dataset.merchantId = String(merchant.id);
    const aliasField = document.getElementById('merchant_alias');
    if (aliasField) {
      aliasField.value = merchant.short_name || '';
    }
    this.ensureSelectOption(merchant);
    this.select.value = String(merchant.id);
    this.hideSuggestions();
    this.hideSuggestion();
    this.renderAssociationState();
    this.input.dispatchEvent(
      new CustomEvent('merchant-selected', {
        bubbles: true,
        detail: { merchant },
      }),
    );
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
    if (this.quickAddServiceLevel) this.quickAddServiceLevel.value = '';
    if (this.quickAddCuisine) this.quickAddCuisine.value = '';
    if (this.quickAddMenuFocus) this.quickAddMenuFocus.value = '';
    if (this.quickAddCategory) this.quickAddCategory.value = '';
    if (this.quickAddWebsite) this.quickAddWebsite.value = '';
    if (this.quickAddError) this.quickAddError.classList.add('d-none');
    const modal = new bootstrap.Modal(this.quickAddModal);
    modal.show();
  }

  async submitQuickAdd() {
    if (!this.quickAddName || !this.quickAddSubmit) return;
    const name = this.quickAddName.value.trim();
    const shortName = this.quickAddShortName ? this.quickAddShortName.value.trim() : '';
    const serviceLevel = this.quickAddServiceLevel ? this.quickAddServiceLevel.value.trim() : '';
    const cuisine = this.quickAddCuisine ? this.quickAddCuisine.value.trim() : '';
    const menuFocus = this.quickAddMenuFocus ? this.quickAddMenuFocus.value.trim() : '';
    const category = this.quickAddCategory ? this.quickAddCategory.value.trim() : '';
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
        body: JSON.stringify({
          name,
          short_name: shortName,
          service_level: serviceLevel,
          cuisine,
          menu_focus: menuFocus,
          category,
          website,
        }),
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

  renderAssociationState() {
    const hasMerchant = Boolean(this.selectedMerchant && this.selectedMerchant.id);

    if (this.summary) {
      this.summary.classList.toggle('d-none', !hasMerchant);
    }
    if (this.emptyState) {
      this.emptyState.classList.toggle('d-none', hasMerchant);
    }

    if (!hasMerchant) return;

    if (this.summaryName) {
      this.summaryName.textContent = this.selectedMerchant.name || '';
    }

    if (this.summaryMeta) {
      const metaParts = [];
      if (this.selectedMerchant.short_name) {
        metaParts.push(`Alias: ${this.selectedMerchant.short_name}`);
      }
      metaParts.push(`Brand: ${this.selectedMerchant.is_chain ? 'Chain Brand' : 'Independent Brand'}`);
      if (this.selectedMerchant.service_level) {
        metaParts.push(
          `Service: ${String(this.selectedMerchant.service_level_display || this.selectedMerchant.service_level).replace(/_/g, ' ')}`,
        );
      }
      if (this.selectedMerchant.cuisine) {
        metaParts.push(`Cuisine: ${this.selectedMerchant.cuisine}`);
      }
      if (this.selectedMerchant.menu_focus) {
        metaParts.push(`Menu: ${this.selectedMerchant.menu_focus}`);
      }
      if (this.selectedMerchant.category) {
        metaParts.push(
          `Format: ${String(this.selectedMerchant.category_display || this.selectedMerchant.category).replace(/_/g, ' ')}`,
        );
      }
      if (this.selectedMerchant.website) {
        metaParts.push(this.selectedMerchant.website);
      }
      this.summaryMeta.innerHTML = metaParts.map((part) => `<span>${escapeHtml(part)}</span>`).join('');
    }

    if (this.viewLink) {
      this.viewLink.href = this.selectedMerchant.view_url || `/restaurants/merchants/${this.selectedMerchant.id}`;
      this.viewLink.classList.remove('d-none');
    }
  }

  async refreshSuggestion() {
    if (!this.suggestionPanel || !this.restaurantNameField) return;
    if (this.selectedMerchant && this.selectedMerchant.id) {
      this.hideSuggestion();
      return;
    }

    const restaurantName = this.restaurantNameField.value.trim();
    if (!restaurantName) {
      this.hideSuggestion();
      return;
    }

    try {
      const params = new URLSearchParams({ restaurant_name: restaurantName });
      const response = await fetch(`/restaurants/merchants/api/suggest?${params.toString()}`, {
        method: 'GET',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
      });

      if (!response.ok) {
        this.hideSuggestion();
        return;
      }

      const data = await response.json();
      if (!data?.merchant) {
        this.hideSuggestion();
        return;
      }

      this.suggestedMerchant = data.merchant;
      this.renderSuggestion();
    } catch {
      this.hideSuggestion();
    }
  }

  renderSuggestion() {
    if (!this.suggestionPanel || !this.suggestedMerchant) return;

    if (this.suggestionName) {
      this.suggestionName.textContent = this.suggestedMerchant.name || '';
    }
    if (this.suggestionMeta) {
      const metaParts = [];
      if (this.suggestedMerchant.short_name) {
        metaParts.push(`Alias: ${this.suggestedMerchant.short_name}`);
      }
      metaParts.push(`Brand: ${this.suggestedMerchant.is_chain ? 'Chain Brand' : 'Independent Brand'}`);
      if (this.suggestedMerchant.service_level) {
        metaParts.push(`Service: ${String(this.suggestedMerchant.service_level_display || this.suggestedMerchant.service_level).replace(/_/g, ' ')}`);
      }
      if (this.suggestedMerchant.cuisine) {
        metaParts.push(`Cuisine: ${this.suggestedMerchant.cuisine}`);
      }
      if (this.suggestedMerchant.menu_focus) {
        metaParts.push(`Menu: ${this.suggestedMerchant.menu_focus}`);
      }
      if (this.suggestedMerchant.category) {
        metaParts.push(`Format: ${String(this.suggestedMerchant.category_display || this.suggestedMerchant.category).replace(/_/g, ' ')}`);
      }
      this.suggestionMeta.innerHTML = metaParts.map((part) => `<span>${escapeHtml(part)}</span>`).join('');
    }

    this.suggestionPanel.classList.remove('d-none');
  }

  hideSuggestion() {
    this.suggestedMerchant = null;
    if (this.suggestionPanel) {
      this.suggestionPanel.classList.add('d-none');
    }
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
