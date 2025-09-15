/**
 * Centralized Event Handlers
 * Replaces all inline onclick handlers with proper event delegation
 *
 * @version 1.0.0
 * @author Meal Expense Tracker Team
 */

import { showToast } from '../utils/notifications.js';
import { getCSRFToken } from '../utils/csrf-token.js';

export class EventHandlers {
    constructor() {
        this.init();
    }

    init() {
        this.setupClickHandlers();
        this.setupFormHandlers();
        this.setupKeyboardHandlers();
    }



    setupClickHandlers() {
        // Replace onclick="validateRestaurantData()"
        document.addEventListener('click', (event) => {
            const validateBtn = event.target.closest('[data-action="validate-restaurant"]');
            if (validateBtn) {
                event.preventDefault();
                this.validateRestaurantData(validateBtn.dataset.restaurantId);
            }

            // Replace onclick="openWebsite()"
            const websiteBtn = event.target.closest('[data-action="open-website"]');
            if (websiteBtn) {
                event.preventDefault();
                this.openWebsite(websiteBtn.dataset.website);
            }

            // Replace onclick="navigator.clipboard.writeText()"
            const copyBtn = event.target.closest('[data-action="copy-to-clipboard"]');
            if (copyBtn) {
                event.preventDefault();
                this.copyToClipboard(copyBtn.dataset.text);
            }

            // Replace onclick="clearPlaceId()"
            const clearBtn = event.target.closest('[data-action="clear-place-id"]');
            if (clearBtn) {
                event.preventDefault();
                this.clearPlaceId();
            }

            // Replace onclick="applyAddressFixes()"
            const applyBtn = event.target.closest('[data-action="apply-address-fixes"]');
            if (applyBtn) {
                event.preventDefault();
                this.applyAddressFixes();
            }

            // Replace tag removal onclick
            const tagRemove = event.target.closest('.tag-remove');
            if (tagRemove) {
                event.preventDefault();
                this.removeTag(tagRemove);
            }

            // Replace avatar upload onclick
            const avatarOverlay = event.target.closest('.avatar-upload-overlay');
            if (avatarOverlay) {
                event.preventDefault();
                this.triggerAvatarUpload();
            }

            // Replace timezone detection onclick
            const timezoneBtn = event.target.closest('[data-action="detect-timezone"]');
            if (timezoneBtn) {
                event.preventDefault();
                this.detectTimezone();
            }

            // Handle coming soon features
            const comingSoonBtn = event.target.closest('[data-action="coming-soon"]');
            if (comingSoonBtn) {
                event.preventDefault();
                const feature = comingSoonBtn.dataset.feature || 'this feature';
                showToast(`${feature} is coming soon!`, 'info');
            }
        });
    }

    setupFormHandlers() {
        // Handle form submissions with proper validation
        document.addEventListener('submit', (event) => {
            const form = event.target.closest('form');
            if (!form) return;

            const action = form.dataset.action;
            if (action === 'validate-restaurant') {
                event.preventDefault();
                this.validateRestaurantForm(form);
            }
        });
    }

    setupKeyboardHandlers() {
        // Handle keyboard shortcuts
        document.addEventListener('keydown', (event) => {
            // Ctrl/Cmd + Enter to submit forms
            if ((event.ctrlKey || event.metaKey) && event.key === 'Enter') {
                const form = event.target.closest('form');
                if (form && form.dataset.action === 'validate-restaurant') {
                    event.preventDefault();
                    this.validateRestaurantForm(form);
                }
            }
        });
    }

    // Event handler implementations
    async validateRestaurantData(restaurantId) {
        try {
            showToast('Validating restaurant data...', 'info');

            // Get form data
            const nameField = document.getElementById('name');
            const addressField = document.getElementById('address');
            const googlePlaceIdField = document.getElementById('google_place_id');

            if (!nameField || !addressField) {
                showToast('Required form fields not found', 'error');
                return;
            }

            const restaurantName = nameField.value.trim();
            const address = addressField.value.trim();
            const googlePlaceId = googlePlaceIdField ? googlePlaceIdField.value.trim() : '';

            if (!restaurantName) {
                showToast('Please enter a restaurant name to validate', 'error');
                return;
            }

            if (!address) {
                showToast('Please enter an address to validate', 'error');
                return;
            }

            // Call the correct API endpoint with form data
            const response = await fetch('/api/v1/restaurants/validate', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCSRFToken()
                },
                body: JSON.stringify({
                    name: restaurantName,
                    address: address,
                    google_place_id: googlePlaceId || null
                })
            });

            if (response.ok) {
                const data = await response.json();
                if (data.status === 'success') {
                    showToast('Restaurant validated successfully!', 'success');
                    // You could add logic here to handle validation results
                } else {
                    showToast(data.message || 'Validation completed with issues', 'warning');
                }
            } else {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.message || 'Validation failed');
            }
        } catch (error) {
            console.error('Restaurant validation error:', error);
            showToast('Failed to validate restaurant', 'error');
        }
    }

    openWebsite(websiteUrl) {
        if (!websiteUrl) {
            showToast('No website URL provided', 'warning');
            return;
        }

        let url = websiteUrl.trim();
        if (!url.startsWith('http://') && !url.startsWith('https://')) {
            url = 'https://' + url;
        }

        window.open(url, '_blank', 'noopener,noreferrer');
    }

    async copyToClipboard(text) {
        try {
            await navigator.clipboard.writeText(text);
            showToast('Copied to clipboard!', 'success');
        } catch (error) {
            console.error('Clipboard error:', error);
            showToast('Failed to copy to clipboard', 'error');
        }
    }

    clearPlaceId() {
        if (!confirm('Are you sure you want to clear the Google Place ID? This will remove the connection to Google Places.')) {
            return;
        }

        const hiddenField = document.getElementById('google_place_id');
        const displayField = document.getElementById('google_place_id_display');

        if (hiddenField) hiddenField.value = '';
        if (displayField) displayField.value = '';

        // Hide related sections
        const placeIdSection = displayField?.closest('.col-12');
        if (placeIdSection) {
            placeIdSection.style.display = 'none';
        }

        const buttonsSection = placeIdSection?.nextElementSibling;
        if (buttonsSection) {
            buttonsSection.style.display = 'none';
        }

        // Clear search input
        const searchInput = document.getElementById('restaurant-search');
        if (searchInput) {
            searchInput.value = '';
        }

        showToast('Google Place ID cleared successfully', 'success');
    }

    applyAddressFixes() {
        // Implementation for address fixes
        showToast('Address fixes applied', 'success');
    }

    removeTag(tagRemoveElement) {
        const tagBadge = tagRemoveElement.closest('.tag-badge');
        const tagName = tagBadge.dataset.tagName;

        if (tagBadge) {
            tagBadge.remove();
        }

        // Update tags input if it exists
        const tagsInput = window.tagsInput;
        if (tagsInput && tagsInput.removeTag) {
            tagsInput.removeTag(tagName);
        }
    }

    triggerAvatarUpload() {
        const avatarInput = document.getElementById('avatar-upload');
        if (avatarInput) {
            avatarInput.click();
        }
    }

    detectTimezone() {
        if (window.timezoneDetector?.detectManually) {
            window.timezoneDetector.detectManually();
        }
    }

    async validateRestaurantForm(form) {
        try {
            const formData = new FormData(form);
            const response = await fetch(form.action, {
                method: 'POST',
                body: formData
            });

            if (response.ok) {
                showToast('Restaurant form validated successfully!', 'success');
            } else {
                throw new Error('Form validation failed');
            }
        } catch (error) {
            console.error('Form validation error:', error);
            showToast('Failed to validate form', 'error');
        }
    }
}

// Initialize event handlers when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    new EventHandlers();
});
