/**
 * Restaurant Form Module
 * Extracted from restaurants/form.html to separate concerns
 *
 * @version 1.0.0
 * @author Meal Expense Tracker Team
 */

import { showToast } from '../utils/notifications.js';

export class RestaurantForm {
    constructor() {
        this.form = null;
        this.init();
    }

    init() {
        this.form = document.querySelector('form[action*="restaurants"]');
        if (!this.form) return;

        this.setupFormValidation();
        this.setupWebsiteButton();
        this.setupValidationButton();
        this.setupAddressValidation();
    }

    setupFormValidation() {
        // Category dropdown enhancement
        const categorySelect = document.querySelector('[data-category-select]');
        if (categorySelect) {
            this.updateCategoryStyle(categorySelect);
            categorySelect.addEventListener('change', () => this.updateCategoryStyle(categorySelect));
        }
    }

    updateCategoryStyle(categorySelect) {
        const selectedOption = categorySelect.options[categorySelect.selectedIndex];
        if (selectedOption && selectedOption.dataset.color) {
            categorySelect.style.backgroundColor = selectedOption.dataset.color + '20';
            categorySelect.style.borderColor = selectedOption.dataset.color + '40';
            categorySelect.style.color = selectedOption.dataset.color;
        } else {
            categorySelect.style.backgroundColor = '';
            categorySelect.style.borderColor = '';
            categorySelect.style.color = '';
        }
    }

    setupWebsiteButton() {
        const websiteField = document.getElementById('website');
        const websiteBtn = document.getElementById('open-website-btn');

        if (websiteField && websiteBtn) {
            this.updateWebsiteButton(websiteField, websiteBtn);
            websiteField.addEventListener('input', () => this.updateWebsiteButton(websiteField, websiteBtn));
        }
    }

    updateWebsiteButton(websiteField, websiteBtn) {
        const hasValue = websiteField.value.trim().length > 0;
        websiteBtn.disabled = !hasValue;
    }

    setupValidationButton() {
        const nameField = document.getElementById('name');
        const addressField = document.getElementById('address');
        const validateBtn = document.getElementById('validate-restaurant-btn');

        if (nameField && addressField && validateBtn) {
            this.updateValidationButton(nameField, addressField, validateBtn);

            nameField.addEventListener('input', () => this.updateValidationButton(nameField, addressField, validateBtn));
            addressField.addEventListener('input', () => this.updateValidationButton(nameField, addressField, validateBtn));
        }
    }

    updateValidationButton(nameField, addressField, validateBtn) {
        const hasName = nameField.value.trim().length > 0;
        const hasAddress = addressField.value.trim().length > 0;
        validateBtn.disabled = !(hasName && hasAddress);
    }

    setupAddressValidation() {
        const addressField = document.getElementById('address');
        if (!addressField) return;

        addressField.addEventListener('blur', () => this.validateAddress(addressField));
        addressField.addEventListener('input', () => this.clearAddressError(addressField));
    }

    async validateAddress(addressField) {
        const address = addressField.value.trim();
        if (address.length < 5) return; // Skip validation for short addresses

        try {
            const response = await fetch('/restaurants/validate-address', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ address })
            });

            const data = await response.json();

            if (data.valid) {
                this.showAddressSuccess(addressField);
            } else {
                this.showAddressError(addressField, data.suggestions);
            }
        } catch (error) {
            console.error('Address validation error:', error);
        }
    }

    showAddressSuccess(addressField) {
        const errorDiv = document.getElementById('address-error');
        if (errorDiv) {
            errorDiv.textContent = '✓ Address validated';
            errorDiv.className = 'text-success small mt-1';
            errorDiv.classList.remove('d-none');
        }
    }

    showAddressError(addressField, suggestions) {
        const errorDiv = document.getElementById('address-error');
        if (errorDiv) {
            errorDiv.textContent = 'Address may need correction';
            errorDiv.className = 'text-warning small mt-1';
            errorDiv.classList.remove('d-none');
        }

        // Show suggestions if available
        if (suggestions && suggestions.length > 0) {
            this.showAddressSuggestions(suggestions);
        }
    }

    showAddressSuggestions(suggestions) {
        const suggestionsContainer = document.getElementById('address-suggestions');
        if (!suggestionsContainer) return;

        suggestionsContainer.innerHTML = suggestions.map(suggestion =>
            `<div class="suggestion-item p-2 border-bottom" data-address="${suggestion}">${suggestion}</div>`
        ).join('');

        suggestionsContainer.classList.remove('d-none');

        // Add click handlers for suggestions
        suggestionsContainer.querySelectorAll('.suggestion-item').forEach(item => {
            item.addEventListener('click', () => {
                document.getElementById('address').value = item.dataset.address;
                suggestionsContainer.classList.add('d-none');
                this.clearAddressError(document.getElementById('address'));
            });
        });
    }

    clearAddressError(addressField) {
        const errorDiv = document.getElementById('address-error');
        if (errorDiv) {
            errorDiv.classList.add('d-none');
        }

        const suggestionsContainer = document.getElementById('address-suggestions');
        if (suggestionsContainer) {
            suggestionsContainer.classList.add('d-none');
        }
    }

    // Public API methods
    validateForm() {
        const formData = new FormData(this.form);
        const requiredFields = ['name', 'address'];

        for (const field of requiredFields) {
            if (!formData.get(field)?.trim()) {
                showToast(`Please fill in the ${field} field`, 'warning');
                return false;
            }
        }

        return true;
    }

    submitForm() {
        if (!this.validateForm()) return;

        this.form.submit();
    }

    resetForm() {
        this.form.reset();
        this.updateCategoryStyle(document.querySelector('[data-category-select]'));
        this.updateWebsiteButton(document.getElementById('website'), document.getElementById('open-website-btn'));
        this.updateValidationButton(document.getElementById('name'), document.getElementById('address'), document.getElementById('validate-restaurant-btn'));
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    new RestaurantForm();
});
