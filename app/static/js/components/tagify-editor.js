/**
 * Tagify-based Tag Editor Component
 * Handles tag editing functionality using Tagify for consistency
 */

class TagifyEditor {
    constructor() {
        this.modal = null;
        this.form = null;
        this.tagifyInstance = null;
        this.isInitialized = false;
        this.currentExpenseId = null;
    }

    /**
     * Initialize the tag editor
     */
    init() {
        if (this.isInitialized) return;

        this.modal = document.getElementById('tagEditorModal');
        this.form = document.getElementById('tagEditorForm');

        if (!this.modal || !this.form) {
            console.warn('Tag editor modal not found in DOM');
            return;
        }

        this.setupEventListeners();
        this.setupTagify();
        this.isInitialized = true;
    }

    /**
     * Setup event listeners for the tag editor
     */
    setupEventListeners() {
        const saveBtn = document.getElementById('saveTagBtn');
        const deleteBtn = document.getElementById('deleteTagBtn');

        // Save tags
        if (saveBtn) {
            saveBtn.addEventListener('click', () => this.saveTags());
        }

        // Delete all tags
        if (deleteBtn) {
            deleteBtn.addEventListener('click', () => this.deleteAllTags());
        }

        // Reset modal when hidden
        this.modal.addEventListener('hidden.bs.modal', () => {
            this.resetForm();
        });

        // Load existing tags when modal is shown
        this.modal.addEventListener('shown.bs.modal', () => {
            this.loadExistingTags();
        });
    }

    /**
     * Setup Tagify for the tag editor
     */
    setupTagify() {
        const tagsInput = document.querySelector('#tagEditorModal [data-tags-input]');
        if (!tagsInput) {
            console.warn('Tagify input not found in tag editor modal');
            return;
        }

        // Check if Tagify is loaded
        if (typeof Tagify === 'undefined') {
            console.warn('Tagify library not loaded, loading it now...');
            this.loadTagifyLibrary().then(() => {
                this.initializeTagify(tagsInput);
            }).catch((error) => {
                console.error('Failed to load Tagify library:', error);
                // Fallback: show a simple text input
                this.setupFallbackInput(tagsInput);
            });
            return;
        }

        this.initializeTagify(tagsInput);
    }

    /**
     * Load Tagify library dynamically
     */
    async loadTagifyLibrary() {
        return new Promise((resolve, reject) => {
            // Check if already loaded
            if (typeof Tagify !== 'undefined') {
                resolve();
                return;
            }

            // Load CSS
            const cssLink = document.createElement('link');
            cssLink.rel = 'stylesheet';
            cssLink.href = 'https://cdn.jsdelivr.net/npm/@yaireo/tagify@4.17.9/dist/tagify.css';
            document.head.appendChild(cssLink);

            // Load JS
            const script = document.createElement('script');
            script.src = 'https://cdn.jsdelivr.net/npm/@yaireo/tagify@4.17.9/dist/tagify.min.js';
            script.onload = () => {
                console.log('Tagify library loaded successfully');
                resolve();
            };
            script.onerror = () => {
                console.error('Failed to load Tagify library');
                reject(new Error('Failed to load Tagify library'));
            };
            document.head.appendChild(script);
        });
    }

    /**
     * Initialize Tagify instance
     */
    initializeTagify(tagsInput) {
        try {
            this.tagifyInstance = new Tagify(tagsInput, {
                whitelist: [],
                maxTags: 20,
                enforceWhitelist: false,
                addTagOnBlur: true,
                duplicates: false,
                dropdown: {
                    enabled: 0,
                    closeOnSelect: false,
                    highlightFirst: true,
                    searchKeys: ['value', 'name']
                },
                templates: {
                    tag: (tagData) => {
                        const colorClass = `tag-color-${(tagData.value.length % 12) + 1}`;
                        return `
                            <tag title="${tagData.title || tagData.value}"
                                 contenteditable='false'
                                 spellcheck='false'
                                 tabIndex="-1"
                                 class="tagify__tag ${colorClass}"
                                 data-tagify-tag="true"
                                 data-autofill-safe="true"
                                 data-extension-safe="true">
                                <x title='' class='tagify__tag__removeBtn' role='button' aria-label='remove tag'></x>
                                <div>
                                    <span class='tagify__tag-text'>${tagData.value}</span>
                                </div>
                            </tag>
                        `;
                    },
                    dropdownItem: (tagData) => {
                        const colorClass = `tag-color-${(tagData.value.length % 12) + 1}`;
                        return `
                            <div class="tagify__dropdown__item" data-value="${tagData.value}">
                                <span class="tagify__tag ${colorClass}" style="margin: 0; font-size: 0.7rem; padding: 0.2rem 0.4rem;">
                                    ${tagData.value}
                                </span>
                            </div>
                        `;
                    }
                }
            });

            // Load initial whitelist
            this.loadTagWhitelist();

            // Setup search functionality
            this.tagifyInstance.on('input', (e) => {
                const value = e.detail.value;
                if (value.length < 1) return;

                this.searchTags(value);
            });

            console.log('Tagify editor initialized successfully');
        } catch (error) {
            console.error('Error initializing Tagify editor:', error);
        }
    }

    /**
     * Setup fallback input when Tagify fails to load
     */
    setupFallbackInput(tagsInput) {
        console.warn('Using fallback text input for tag editing');
        tagsInput.placeholder = 'Enter tags separated by commas (e.g., work, urgent, travel)';
        tagsInput.style.border = '1px solid #dc3545';
        tagsInput.style.backgroundColor = '#f8d7da';

        // Add a warning message
        const warning = document.createElement('div');
        warning.className = 'alert alert-warning mt-2';
        warning.innerHTML = '<i class="fas fa-exclamation-triangle me-1"></i>Tagify library failed to load. Using simple text input.';
        tagsInput.parentNode.insertBefore(warning, tagsInput.nextSibling);
    }

    /**
     * Load tag whitelist for autocomplete
     */
    async loadTagWhitelist() {
        try {
            const response = await fetch('/expenses/tags');
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            const data = await response.json();
            if (data.success && Array.isArray(data.tags)) {
                const whitelist = data.tags.map(tag => ({
                    value: tag.name,
                    name: tag.name,
                    color: tag.color
                }));
                this.tagifyInstance.settings.whitelist = whitelist;
                console.log('Loaded tag whitelist:', whitelist);
            }
        } catch (error) {
            console.error('Error loading tag whitelist:', error);
        }
    }

    /**
     * Search for tags
     */
    async searchTags(query) {
        try {
            const response = await fetch(`/expenses/tags/search?q=${encodeURIComponent(query)}`);
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            const data = await response.json();
            if (data.success && Array.isArray(data.tags)) {
                const suggestions = data.tags.map(tag => ({
                    value: tag.name,
                    name: tag.name,
                    color: tag.color
                }));
                this.tagifyInstance.settings.whitelist = suggestions;
                this.tagifyInstance.dropdown.show.call(this.tagifyInstance, query);
            }
        } catch (error) {
            console.error('Error searching tags:', error);
        }
    }

    /**
     * Edit tags for an expense
     */
    async editExpenseTags(expenseId) {
        if (!this.isInitialized) {
            this.init();
        }

        this.currentExpenseId = expenseId;

        // Load current tags for this expense
        await this.loadExpenseTags(expenseId);

        // Show modal
        const modalInstance = new bootstrap.Modal(this.modal);
        modalInstance.show();
    }

    /**
     * Load current tags for an expense
     */
    async loadExpenseTags(expenseId) {
        try {
            const response = await fetch(`/expenses/${expenseId}/tags`);
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            const data = await response.json();
            if (data.success && Array.isArray(data.tags)) {
                const tagNames = data.tags.map(tag => tag.name);

                // Handle both Tagify instance and fallback text input
                if (this.tagifyInstance) {
                    this.tagifyInstance.removeAllTags();
                    this.tagifyInstance.addTags(tagNames);
                } else {
                    // Fallback: set text input value
                    const tagsInput = document.querySelector('#tagEditorModal [data-tags-input]');
                    if (tagsInput) {
                        tagsInput.value = tagNames.join(', ');
                    }
                }
                console.log('Loaded expense tags:', tagNames);
            }
        } catch (error) {
            console.error('Error loading expense tags:', error);
        }
    }

    /**
     * Load existing tags for display
     */
    async loadExistingTags() {
        const container = document.getElementById('existingTagsContainer');
        if (!container) return;

        try {
            container.innerHTML = '<div class="text-muted small">Loading existing tags...</div>';

            const response = await fetch('/expenses/tags');
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            const data = await response.json();
            if (data.success && Array.isArray(data.tags)) {
                const tags = data.tags;

                if (tags.length === 0) {
                    container.innerHTML = '<div class="text-muted small">No existing tags found.</div>';
                    return;
                }

                container.innerHTML = '';
                tags.forEach(tag => {
                    const tagElement = document.createElement('span');
                    tagElement.className = 'tag-badge tag-editable';
                    tagElement.setAttribute('data-tag-id', tag.id);
                    tagElement.setAttribute('data-tag-name', tag.name);
                    tagElement.setAttribute('data-tag-color', tag.color);
                    tagElement.setAttribute('data-tag-description', tag.description || '');
                    tagElement.style.backgroundColor = tag.color;
                    tagElement.style.cursor = 'pointer';
                    tagElement.textContent = tag.name;

                    // Add click handler to add tag to Tagify
                    tagElement.addEventListener('click', () => {
                        this.tagifyInstance.addTags(tag.name);
                    });

                    container.appendChild(tagElement);
                });
            }
        } catch (error) {
            console.error('Error loading existing tags:', error);
            container.innerHTML = '<div class="text-danger small">Error loading existing tags.</div>';
        }
    }

    /**
     * Save tags for the current expense
     */
    async saveTags() {
        if (!this.currentExpenseId) {
            alert('No expense selected');
            return;
        }

        let tagNames = [];

        // Handle both Tagify instance and fallback text input
        if (this.tagifyInstance && this.tagifyInstance.value) {
            tagNames = this.tagifyInstance.value.map(tag => tag.value);
        } else {
            // Fallback: parse comma-separated values from text input
            const tagsInput = document.querySelector('#tagEditorModal [data-tags-input]');
            if (tagsInput) {
                const value = tagsInput.value.trim();
                tagNames = value ? value.split(',').map(tag => tag.trim()).filter(tag => tag) : [];
            }
        }

        try {
            const response = await fetch(`/expenses/${this.currentExpenseId}/tags`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': document.querySelector('input[name="csrf_token"]')?.value || ''
                },
                body: JSON.stringify({ tags: tagNames })
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const result = await response.json();

            if (result.success) {
                // Close modal
                const modalInstance = bootstrap.Modal.getInstance(this.modal);
                if (modalInstance) {
                    modalInstance.hide();
                }

                // Trigger custom event for other components to listen to
                document.dispatchEvent(new CustomEvent('expenseTagsUpdated', {
                    detail: { expenseId: this.currentExpenseId, tags: result.tags }
                }));

                // Reload page if no custom handler is set up
                if (!document.querySelector('[data-tag-editor-custom-handler]')) {
                    location.reload();
                }
            } else {
                alert('Error: ' + result.message);
            }
        } catch (error) {
            console.error('Error saving tags:', error);
            alert('Error saving tags. Please try again.');
        }
    }

    /**
     * Delete all tags for the current expense
     */
    async deleteAllTags() {
        if (!this.currentExpenseId) {
            alert('No expense selected');
            return;
        }

        if (!confirm('Are you sure you want to remove all tags from this expense?')) {
            return;
        }

        try {
            const response = await fetch(`/expenses/${this.currentExpenseId}/tags`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': document.querySelector('input[name="csrf_token"]')?.value || ''
                },
                body: JSON.stringify({ tags: [] })
            });

            const result = await response.json();

            if (result.success) {
                // Close modal
                const modalInstance = bootstrap.Modal.getInstance(this.modal);
                if (modalInstance) {
                    modalInstance.hide();
                }

                // Trigger custom event for other components to listen to
                document.dispatchEvent(new CustomEvent('expenseTagsUpdated', {
                    detail: { expenseId: this.currentExpenseId, tags: [] }
                }));

                // Reload page if no custom handler is set up
                if (!document.querySelector('[data-tag-editor-custom-handler]')) {
                    location.reload();
                }
            } else {
                alert('Error: ' + result.message);
            }
        } catch (error) {
            console.error('Error deleting tags:', error);
            alert('Error deleting tags. Please try again.');
        }
    }

    /**
     * Reset the form
     */
    resetForm() {
        if (this.tagifyInstance) {
            this.tagifyInstance.removeAllTags();
        } else {
            // Fallback: clear text input
            const tagsInput = document.querySelector('#tagEditorModal [data-tags-input]');
            if (tagsInput) {
                tagsInput.value = '';
            }
        }
        this.currentExpenseId = null;
    }
}

// Global tagify editor instance
window.tagifyEditor = new TagifyEditor();

// Auto-initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        window.tagifyEditor.init();
    });
} else {
    window.tagifyEditor.init();
}

// Export for module usage
export default TagifyEditor;
