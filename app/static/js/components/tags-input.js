/**
 * Tags Input Component
 * Provides Jira-style tag input with autocomplete and tag management
 */

class TagsInput {
    constructor(container, options = {}) {
        this.container = container;
        this.options = {
            apiEndpoint: '/expenses/tags',
            searchEndpoint: '/expenses/tags/search',
            createEndpoint: '/expenses/tags',
            expenseId: null,
            ...options
        };

        this.tags = new Set();
        this.suggestions = [];
        this.selectedSuggestionIndex = -1;
        this.debounceTimer = null;

        this.init();
    }

    init() {
        this.createElements();
        this.bindEvents();
        this.loadExistingTags();
    }

    createElements() {
        // Create tags display area
        this.tagsDisplay = document.createElement('div');
        this.tagsDisplay.className = 'tags-display';
        this.tagsDisplay.id = 'tagsDisplay';

        // Create input field
        this.input = document.createElement('input');
        this.input.type = 'text';
        this.input.className = 'form-control tags-input';
        this.input.id = 'tagsInput';
        this.input.placeholder = 'Type to add tags...';
        this.input.autocomplete = 'off';

        // Create suggestions dropdown
        this.suggestionsContainer = document.createElement('div');
        this.suggestionsContainer.className = 'tags-suggestions';
        this.suggestionsContainer.id = 'tagsSuggestions';
        this.suggestionsContainer.style.display = 'none';

        // Create wrapper
        this.wrapper = document.createElement('div');
        this.wrapper.className = 'tags-input-wrapper';
        this.wrapper.appendChild(this.tagsDisplay);
        this.wrapper.appendChild(this.input);

        // Create container
        this.inputContainer = document.createElement('div');
        this.inputContainer.className = 'tags-input-container';
        this.inputContainer.appendChild(this.wrapper);
        this.inputContainer.appendChild(this.suggestionsContainer);

        // Replace the original container content
        this.container.innerHTML = '';
        this.container.appendChild(this.inputContainer);
    }

    bindEvents() {
        // Input events
        this.input.addEventListener('input', (e) => this.handleInput(e));
        this.input.addEventListener('keydown', (e) => this.handleKeydown(e));
        this.input.addEventListener('focus', () => this.showSuggestions());
        this.input.addEventListener('blur', () => this.hideSuggestions());

        // Click events
        this.inputContainer.addEventListener('click', (e) => {
            if (e.target === this.inputContainer || e.target === this.wrapper) {
                this.input.focus();
            }
        });

        // Suggestion clicks
        this.suggestionsContainer.addEventListener('click', (e) => {
            const item = e.target.closest('.tags-suggestion-item');
            if (item) {
                const tagName = item.dataset.tagName;
                this.addTag(tagName);
                this.hideSuggestions();
                this.input.focus();
            }
        });
    }

    async loadExistingTags() {
        if (!this.options.expenseId) return;

        try {
            const response = await fetch(`${this.options.apiEndpoint}/${this.options.expenseId}/tags`);
            const data = await response.json();

            if (data.success) {
                data.tags.forEach(tag => {
                    this.tags.add(tag.name);
                    this.renderTag(tag);
                });
            }
        } catch (error) {
            console.error('Error loading existing tags:', error);
        }
    }

    handleInput(e) {
        const query = e.target.value.trim();

        // Clear debounce timer
        if (this.debounceTimer) {
            clearTimeout(this.debounceTimer);
        }

        // Debounce search
        this.debounceTimer = setTimeout(() => {
            this.searchTags(query);
        }, 300);
    }

    handleKeydown(e) {
        const suggestions = this.suggestionsContainer.querySelectorAll('.tags-suggestion-item');

        switch (e.key) {
            case 'Enter':
                e.preventDefault();
                if (this.selectedSuggestionIndex >= 0 && suggestions[this.selectedSuggestionIndex]) {
                    const tagName = suggestions[this.selectedSuggestionIndex].dataset.tagName;
                    this.addTag(tagName);
                    this.hideSuggestions();
                } else if (this.input.value.trim()) {
                    this.addTag(this.input.value.trim());
                }
                break;

            case 'ArrowDown':
                e.preventDefault();
                this.selectedSuggestionIndex = Math.min(this.selectedSuggestionIndex + 1, suggestions.length - 1);
                this.updateSuggestionSelection();
                break;

            case 'ArrowUp':
                e.preventDefault();
                this.selectedSuggestionIndex = Math.max(this.selectedSuggestionIndex - 1, -1);
                this.updateSuggestionSelection();
                break;

            case 'Escape':
                this.hideSuggestions();
                this.input.blur();
                break;

            case 'Backspace':
                if (!this.input.value && this.tags.size > 0) {
                    e.preventDefault();
                    this.removeLastTag();
                }
                break;
        }
    }

    async searchTags(query) {
        if (!query) {
            this.hideSuggestions();
            return;
        }

        try {
            const response = await fetch(`${this.options.searchEndpoint}?q=${encodeURIComponent(query)}&limit=10`);
            const data = await response.json();

            if (data.success) {
                this.suggestions = data.tags;
                this.renderSuggestions();
                this.showSuggestions();
            }
        } catch (error) {
            console.error('Error searching tags:', error);
        }
    }

    renderSuggestions() {
        this.suggestionsContainer.innerHTML = '';
        this.selectedSuggestionIndex = -1;

        if (this.suggestions.length === 0) {
            const emptyItem = document.createElement('div');
            emptyItem.className = 'tags-suggestion-item';
            emptyItem.innerHTML = '<span class="suggestion-text">No tags found</span>';
            this.suggestionsContainer.appendChild(emptyItem);
            return;
        }

        this.suggestions.forEach((tag, index) => {
            const item = document.createElement('div');
            item.className = 'tags-suggestion-item';
            item.dataset.tagName = tag.name;

            // Generate color class based on tag name hash
            const colorIndex = (tag.name.length % 12) + 1;

            item.innerHTML = `
                <div class="suggestion-tag tag-color-${colorIndex}">
                    ${tag.name}
                </div>
                <span class="suggestion-text">${tag.description || 'No description'}</span>
            `;

            this.suggestionsContainer.appendChild(item);
        });
    }

    updateSuggestionSelection() {
        const suggestions = this.suggestionsContainer.querySelectorAll('.tags-suggestion-item');

        suggestions.forEach((item, index) => {
            item.classList.toggle('selected', index === this.selectedSuggestionIndex);
        });
    }

    showSuggestions() {
        if (this.suggestions.length > 0 || this.input.value.trim()) {
            this.suggestionsContainer.style.display = 'block';
        }
    }

    hideSuggestions() {
        this.suggestionsContainer.style.display = 'none';
        this.selectedSuggestionIndex = -1;
    }

    async addTag(tagName) {
        if (!tagName || this.tags.has(tagName)) {
            this.input.value = '';
            return;
        }

        // Normalize tag name
        const normalizedName = this.normalizeTagName(tagName);

        try {
            // Try to create or get the tag
            const response = await fetch(this.options.createEndpoint, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCsrfToken()
                },
                body: JSON.stringify({
                    name: normalizedName,
                    color: '#6c757d' // Default color, will be overridden by CSS class
                })
            });

            const data = await response.json();

            if (data.success) {
                this.tags.add(normalizedName);
                this.renderTag(data.tag);

                // Add to expense if we have an expense ID
                if (this.options.expenseId) {
                    await this.addTagToExpense(normalizedName);
                }
            } else {
                console.error('Error creating tag:', data.message);
            }
        } catch (error) {
            console.error('Error adding tag:', error);
        }

        this.input.value = '';
        this.hideSuggestions();
    }

    async addTagToExpense(tagName) {
        try {
            const response = await fetch(`${this.options.apiEndpoint}/${this.options.expenseId}/tags`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCsrfToken()
                },
                body: JSON.stringify({
                    tags: [tagName]
                })
            });

            const data = await response.json();
            if (!data.success) {
                console.error('Error adding tag to expense:', data.message);
            }
        } catch (error) {
            console.error('Error adding tag to expense:', error);
        }
    }

    renderTag(tag) {
        const tagElement = document.createElement('span');
        // Generate color class based on tag name hash
        const colorIndex = (tag.name.length % 12) + 1;
        tagElement.className = `tag-badge tag-color-${colorIndex}`;
        tagElement.dataset.tagName = tag.name;

        tagElement.innerHTML = `
            ${tag.name}
            <span class="tag-remove" onclick="this.closest('.tag-badge').remove(); this.tagsInput.removeTag('${tag.name}');">
                ×
            </span>
        `;

        this.tagsDisplay.appendChild(tagElement);
    }

    removeTag(tagName) {
        this.tags.delete(tagName);

        if (this.options.expenseId) {
            this.removeTagFromExpense(tagName);
        }
    }

    async removeTagFromExpense(tagName) {
        try {
            const response = await fetch(`${this.options.apiEndpoint}/${this.options.expenseId}/tags`, {
                method: 'DELETE',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCsrfToken()
                },
                body: JSON.stringify({
                    tags: [tagName]
                })
            });

            const data = await response.json();
            if (!data.success) {
                console.error('Error removing tag from expense:', data.message);
            }
        } catch (error) {
            console.error('Error removing tag from expense:', error);
        }
    }

    removeLastTag() {
        const tags = Array.from(this.tags);
        if (tags.length > 0) {
            const lastTag = tags[tags.length - 1];
            this.removeTag(lastTag);

            const tagElements = this.tagsDisplay.querySelectorAll('.tag-badge');
            if (tagElements.length > 0) {
                tagElements[tagElements.length - 1].remove();
            }
        }
    }

    normalizeTagName(name) {
        return name.trim().toLowerCase().replace(/\s+/g, '-').replace(/[^a-z0-9-]/g, '');
    }

    getColorClass(tagName) {
        const colorIndex = (tagName.length % 12) + 1;
        return `tag-color-${colorIndex}`;
    }

    getCsrfToken() {
        const token = document.querySelector('meta[name="csrf-token"]');
        return token ? token.getAttribute('content') : '';
    }

    getTags() {
        return Array.from(this.tags);
    }

    setTags(tags) {
        this.tags.clear();
        this.tagsDisplay.innerHTML = '';

        tags.forEach(tag => {
            this.tags.add(tag);
            this.renderTag(tag);
        });
    }

    clear() {
        this.tags.clear();
        this.tagsDisplay.innerHTML = '';
        this.input.value = '';
        this.hideSuggestions();
    }
}

// Initialize tags input on page load
document.addEventListener('DOMContentLoaded', function() {
    const tagsContainers = document.querySelectorAll('[data-tags-input]');

    tagsContainers.forEach(container => {
        const expenseId = container.dataset.expenseId;
        new TagsInput(container, {
            expenseId: expenseId ? parseInt(expenseId) : null
        });
    });
});

// Export for use in other modules
window.TagsInput = TagsInput;
