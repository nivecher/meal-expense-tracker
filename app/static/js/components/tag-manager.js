/**
 * Tag Manager Component
 * Handles creation, editing, and deletion of ALL user tags
 */

class TagManager {
  constructor() {
    this.modal = null;
    this.form = null;
    this.isInitialized = false;
  }

  /**
     * Initialize the tag manager
     */
  init() {
    if (this.isInitialized) return;

    this.modal = document.getElementById('tagEditorModal');
    this.form = document.getElementById('tagEditorForm');

    if (!this.modal || !this.form) {
      console.warn('Tag manager modal not found in DOM');
      return;
    }

    this.setupEventListeners();
    this.isInitialized = true;
  }

  /**
     * Setup event listeners for the tag manager
     */
  setupEventListeners() {
    const tagNameInput = document.getElementById('tagName');
    const tagColorInput = document.getElementById('tagColor');
    const saveBtn = document.getElementById('saveTagBtn');
    const deleteBtn = document.getElementById('deleteTagBtn');
    const resetBtn = document.getElementById('resetFormBtn');
    const colorPresets = document.querySelectorAll('.color-preset');

    // Update preview when inputs change
    if (tagNameInput) {
      tagNameInput.addEventListener('input', () => this.updateTagPreview());
    }
    if (tagColorInput) {
      tagColorInput.addEventListener('input', () => this.updateTagPreview());
    }

    // Color preset buttons
    colorPresets.forEach((btn) => {
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

    // Reset form
    if (resetBtn) {
      resetBtn.addEventListener('click', () => this.resetForm());
    }

    // Reset modal when hidden
    this.modal.addEventListener('hidden.bs.modal', () => {
      this.resetForm();
    });

    // Load all tags when modal is shown
    this.modal.addEventListener('shown.bs.modal', () => {
      this.loadAllTags();
    });
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
     * Load all user tags
     */
  async loadAllTags() {
    const container = document.getElementById('allTagsContainer');
    if (!container) return;

    try {
      container.innerHTML = '<div class="text-muted small">Loading tags...</div>';

      const response = await fetch('/expenses/tags');
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const data = await response.json();
      if (data.success && Array.isArray(data.tags)) {
        const { tags } = data;

        if (tags.length === 0) {
          container.innerHTML = '<div class="text-muted small">No tags created yet. Create your first tag above!</div>';
          return;
        }

        container.innerHTML = '';
        tags.forEach((tag) => {
          const tagElement = document.createElement('span');
          tagElement.className = 'tag-badge tag-editable tag-badge-pretty';
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
      }
    } catch (error) {
      console.error('Error loading all tags:', error);
      container.innerHTML = '<div class="text-danger small">Error loading tags.</div>';
    }
  }

  /**
     * Edit a tag
     */
  editTag(tagId, tagName, tagColor, tagDescription = '') {
    console.log('Editing tag:', { tagId, tagName, tagColor, tagDescription });

    // Populate form
    document.getElementById('tagId').value = tagId;
    document.getElementById('tagName').value = tagName;
    document.getElementById('tagColor').value = tagColor;
    document.getElementById('tagDescription').value = tagDescription;

    // Show delete button for existing tags
    document.getElementById('deleteTagBtn').style.display = 'inline-block';

    // Update preview
    this.updateTagPreview();
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

    const formData = {
      name: tagName,
      color: tagColor,
      description: tagDescription,
    };

    try {
      console.log('Saving tag:', { tagId, formData });

      let response;
      if (tagId) {
        // Update existing tag
        response = await fetch(`/expenses/tags/${tagId}`, {
          method: 'PUT',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': document.querySelector('input[name="csrf_token"]')?.value || '',
          },
          body: JSON.stringify(formData),
        });
      } else {
        // Create new tag
        response = await fetch('/expenses/tags', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': document.querySelector('input[name="csrf_token"]')?.value || '',
          },
          body: JSON.stringify(formData),
        });
      }

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const result = await response.json();

      if (result.success) {
        // Reload all tags
        await this.loadAllTags();

        // Reset form
        this.resetForm();

        // Trigger custom event for other components to listen to
        document.dispatchEvent(new CustomEvent('tagsUpdated', {
          detail: { tagId, tag: result.tag },
        }));
      } else {
        alert(`Error: ${result.message}`);
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
    const tagId = document.getElementById('tagId')?.value;

    if (!tagId) {
      alert('No tag selected for deletion');
      return;
    }

    if (!confirm('Are you sure you want to delete this tag? This will remove it from all expenses.')) {
      return;
    }

    try {
      const response = await fetch(`/expenses/tags/${tagId}`, {
        method: 'DELETE',
        headers: {
          'X-CSRFToken': document.querySelector('input[name="csrf_token"]')?.value || '',
        },
      });

      const result = await response.json();

      if (result.success) {
        // Reload all tags
        await this.loadAllTags();

        // Reset form
        this.resetForm();

        // Trigger custom event for other components to listen to
        document.dispatchEvent(new CustomEvent('tagDeleted', {
          detail: { tagId },
        }));
      } else {
        alert(`Error: ${result.message}`);
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
    this.updateTagPreview();
  }

  /**
     * Convert hex color to RGB
     */
  hexToRgb(hex) {
    const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
    return result ? {
      r: parseInt(result[1], 16),
      g: parseInt(result[2], 16),
      b: parseInt(result[3], 16),
    } : null;
  }
}

// Global tag manager instance
window.tagManager = new TagManager();

// Auto-initialize when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    window.tagManager.init();
  });
} else {
  window.tagManager.init();
}

// Make TagManager available globally
window.TagManager = TagManager;
