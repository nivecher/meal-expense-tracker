/**
 * Tag Editor Component
 * Handles tag editing functionality with modal interface
 */

class TagEditor {
    constructor() {
        this.modal = null;
        this.form = null;
        this.isInitialized = false;
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
        this.setupTagColors();
        this.isInitialized = true;
    }

    /**
     * Setup event listeners for the tag editor
     */
    setupEventListeners() {
        const tagNameInput = document.getElementById('tagName');
        const tagColorInput = document.getElementById('tagColor');
        const saveBtn = document.getElementById('saveTagBtn');
        const deleteBtn = document.getElementById('deleteTagBtn');
        const colorPresets = document.querySelectorAll('.color-preset');

        // Update preview when inputs change
        if (tagNameInput) {
            tagNameInput.addEventListener('input', () => this.updateTagPreview());
        }
        if (tagColorInput) {
            tagColorInput.addEventListener('input', () => this.updateTagPreview());
        }

        // Color preset buttons
        colorPresets.forEach(btn => {
            btn.addEventListener('click', (e) => {
                const color = e.target.getAttribute('data-color');
                if (tagColorInput) {
                    tagColorInput.value = color;
                    this.updateTagPreview();
                }
            });
        });

        // Save tag
        if (saveBtn) {
            saveBtn.addEventListener('click', () => this.saveTag());
        }

        // Delete tag
        if (deleteBtn) {
            deleteBtn.addEventListener('click', () => this.deleteTag());
        }

        // Reset modal when hidden
        this.modal.addEventListener('hidden.bs.modal', () => {
            this.resetForm();
        });

        // Load existing tags when modal is shown
        this.modal.addEventListener('shown.bs.modal', () => {
            this.loadAndDisplayExistingTags();
        });
    }

    /**
     * Setup tag colors from data attributes
     */
    setupTagColors() {
        const tagBadges = document.querySelectorAll('.tag-badge[data-tag-color]');
        tagBadges.forEach(badge => {
            const color = badge.getAttribute('data-tag-color');
            if (color) {
                // Create a unique CSS class for this color
                const colorClass = `tag-color-custom-${color.replace('#', '')}`;

                // Add the class to the badge
                badge.classList.add(colorClass);

                // Create CSS rule if it doesn't exist
                if (!document.querySelector(`style[data-tag-color="${color}"]`)) {
                    const style = document.createElement('style');
                    style.setAttribute('data-tag-color', color);

                    // Calculate text color based on background brightness
                    const rgb = this.hexToRgb(color);
                    const textColor = rgb && (rgb.r * 299 + rgb.g * 587 + rgb.b * 114) / 1000 > 128 ? '#000' : '#fff';

                    style.textContent = `
                        .${colorClass} {
                            background-color: ${color} !important;
                            color: ${textColor} !important;
                        }
                    `;
                    document.head.appendChild(style);
                }
            }
        });
    }

    /**
     * Load and display existing tags
     */
    async loadExistingTags() {
        try {
            const response = await fetch('/expenses/tags');
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            const data = await response.json();
            if (data.success && data.tags) {
                console.log('Loaded existing tags:', data.tags);
                return data.tags;
            }
        } catch (error) {
            console.error('Error loading existing tags:', error);
        }
        return [];
    }

    /**
     * Load and display existing tags in the modal
     */
    async loadAndDisplayExistingTags() {
        const container = document.getElementById('existingTagsContainer');
        if (!container) return;

        try {
            container.innerHTML = '<div class="text-muted small">Loading existing tags...</div>';

            const tags = await this.loadExistingTags();

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

                // Add click handler to edit tag
                tagElement.addEventListener('click', () => {
                    this.editTag(tag.id, tag.name, tag.color, tag.description || '');
                });

                container.appendChild(tagElement);
            });
        } catch (error) {
            console.error('Error displaying existing tags:', error);
            container.innerHTML = '<div class="text-danger small">Error loading existing tags.</div>';
        }
    }

    /**
     * Edit a tag
     * @param {number} tagId - The ID of the tag to edit
     * @param {string} tagName - The current name of the tag
     * @param {string} tagColor - The current color of the tag
     * @param {string} tagDescription - The current description of the tag (optional)
     */
    editTag(tagId, tagName, tagColor, tagDescription = '') {
        if (!this.isInitialized) {
            this.init();
        }

        console.log('Editing tag:', { tagId, tagName, tagColor, tagDescription }); // Debug log

        // Populate form
        document.getElementById('tagId').value = tagId;
        document.getElementById('tagName').value = tagName;
        document.getElementById('tagColor').value = tagColor;
        document.getElementById('tagDescription').value = tagDescription;

        // Show delete button for existing tags
        document.getElementById('deleteTagBtn').style.display = 'inline-block';

        // Update preview
        this.updateTagPreview();

        // Show modal
        const modalInstance = new bootstrap.Modal(this.modal);
        modalInstance.show();
    }

    /**
     * Update the tag preview
     */
    updateTagPreview() {
        const tagName = document.getElementById('tagName')?.value || 'Tag Preview';
        const tagColor = document.getElementById('tagColor')?.value || '#6c757d';
        const tagPreview = document.getElementById('tagPreview');

        if (!tagPreview) return;

        tagPreview.textContent = tagName;
        tagPreview.style.backgroundColor = tagColor;

        // Adjust text color based on background brightness
        const rgb = this.hexToRgb(tagColor);
        if (rgb) {
            const brightness = (rgb.r * 299 + rgb.g * 587 + rgb.b * 114) / 1000;
            tagPreview.style.color = brightness > 128 ? '#000' : '#fff';
        }
    }

    /**
     * Save the tag
     */
    async saveTag() {
        const tagId = document.getElementById('tagId')?.value;
        const tagName = document.getElementById('tagName')?.value?.trim();
        const tagColor = document.getElementById('tagColor')?.value;
        const tagDescription = document.getElementById('tagDescription')?.value?.trim();

        if (!tagName) {
            alert('Tag name is required');
            return;
        }

        if (!tagId) {
            alert('Tag ID is required');
            return;
        }

        const formData = {
            name: tagName,
            color: tagColor,
            description: tagDescription
        };

        try {
            console.log('Saving tag:', { tagId, formData }); // Debug log

            const response = await fetch(`/expenses/tags/${tagId}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': document.querySelector('input[name="csrf_token"]')?.value || ''
                },
                body: JSON.stringify(formData)
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
                document.dispatchEvent(new CustomEvent('tagUpdated', {
                    detail: { tagId, tag: result.tag }
                }));

                // Reload page if no custom handler is set up
                if (!document.querySelector('[data-tag-editor-custom-handler]')) {
                    location.reload();
                }
            } else {
                alert('Error: ' + result.message);
            }
        } catch (error) {
            console.error('Error saving tag:', error);
            alert('Error saving tag. Please try again.');
        }
    }

    /**
     * Delete the tag
     */
    async deleteTag() {
        if (!confirm('Are you sure you want to delete this tag? This will remove it from all expenses.')) {
            return;
        }

        const tagId = document.getElementById('tagId')?.value;

        try {
            const response = await fetch(`/expenses/tags/${tagId}`, {
                method: 'DELETE',
                headers: {
                    'X-CSRFToken': document.querySelector('input[name="csrf_token"]')?.value || ''
                }
            });

            const result = await response.json();

            if (result.success) {
                // Close modal
                const modalInstance = bootstrap.Modal.getInstance(this.modal);
                if (modalInstance) {
                    modalInstance.hide();
                }

                // Trigger custom event for other components to listen to
                document.dispatchEvent(new CustomEvent('tagDeleted', {
                    detail: { tagId }
                }));

                // Reload page if no custom handler is set up
                if (!document.querySelector('[data-tag-editor-custom-handler]')) {
                    location.reload();
                }
            } else {
                alert('Error: ' + result.message);
            }
        } catch (error) {
            console.error('Error deleting tag:', error);
            alert('Error deleting tag. Please try again.');
        }
    }

    /**
     * Reset the form
     */
    resetForm() {
        if (this.form) {
            this.form.reset();
        }
        const deleteBtn = document.getElementById('deleteTagBtn');
        if (deleteBtn) {
            deleteBtn.style.display = 'none';
        }
    }

    /**
     * Convert hex color to RGB
     * @param {string} hex - Hex color string
     * @returns {Object|null} RGB object or null
     */
    hexToRgb(hex) {
        const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
        return result ? {
            r: parseInt(result[1], 16),
            g: parseInt(result[2], 16),
            b: parseInt(result[3], 16)
        } : null;
    }
}

// Global tag editor instance
window.tagEditor = new TagEditor();

// Auto-initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        window.tagEditor.init();
    });
} else {
    window.tagEditor.init();
}

// Export for module usage
export default TagEditor;
