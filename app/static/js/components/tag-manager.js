/**
 * Tag Manager Component
 * Handles creation, editing, and deletion of ALL user tags
 */

class TagManager {
  constructor() {
    this.modal = null;
    this.form = null;
    this.isInitialized = false;
    this.listenersSetup = false;
  }

  /**
   * Initialize tooltips for tag elements
   */
  initializeTooltips() {
    // Dispose existing tooltips to avoid duplicates
    const existingTooltips = document.querySelectorAll('[data-bs-toggle="tooltip"]');
    existingTooltips.forEach((element) => {
      const tooltip = bootstrap.Tooltip.getInstance(element);
      if (tooltip) {
        tooltip.dispose();
      }
    });

    // Initialize new tooltips
    const tooltipTriggerList = document.querySelectorAll('[data-bs-toggle="tooltip"]');
    tooltipTriggerList.forEach((tooltipTriggerEl) => {
      new bootstrap.Tooltip(tooltipTriggerEl); // eslint-disable-line no-new
    });
  }

  /**
     * Initialize the tag manager
     */
  init() {
    if (this.isInitialized) {
      // Re-check modal and form elements in case DOM changed
      this.modal = document.getElementById('tagEditorModal');
      this.form = document.getElementById('tagEditorForm');
      if (this.modal && this.form) {
        return;
      }
    }

    this.modal = document.getElementById('tagEditorModal');
    this.form = document.getElementById('tagEditorForm');

    if (!this.modal || !this.form) {
      console.warn('Tag manager modal not found in DOM. Will retry when modal is opened.');
      // Set up a listener for when modal might be added to DOM
      const checkModal = () => {
        this.modal = document.getElementById('tagEditorModal');
        this.form = document.getElementById('tagEditorForm');
        if (this.modal && this.form && !this.isInitialized) {
          this.setupEventListeners();
          this.isInitialized = true;
        }
      };
      // Check periodically for a short time
      let attempts = 0;
      const interval = setInterval(() => {
        attempts++;
        checkModal();
        if (this.isInitialized || attempts > 10) {
          clearInterval(interval);
        }
      }, 100);
      return;
    }

    this.setupEventListeners();
    this.isInitialized = true;
  }

  /**
     * Setup event listeners for the tag manager
     */
  setupEventListeners() {
    // Prevent duplicate event listeners
    if (this.listenersSetup) {
      return;
    }

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

    // Refresh tags button
    const refreshBtn = document.getElementById('refreshTagsBtn');
    if (refreshBtn) {
      refreshBtn.addEventListener('click', () => this.loadAllTags());
    }

    // Prevent form submission
    if (this.form) {
      this.form.addEventListener('submit', (e) => {
        e.preventDefault();
        this.saveTag();
      });
    }

    // Reset modal when hidden and restore focus
    this.modal.addEventListener('hidden.bs.modal', () => {
      // Clean up any leftover modal backdrops
      const backdrops = document.querySelectorAll('.modal-backdrop');
      backdrops.forEach((backdrop) => {
        backdrop.remove();
      });

      // Remove modal-open class from body if present
      document.body.classList.remove('modal-open');
      document.body.style.overflow = '';
      document.body.style.paddingRight = '';

      // Reset form to clear any unsaved changes
      this.resetForm();

      // Reload all tags to show updated descriptions
      this.loadAllTags();

      // Refresh Tagify instance to show updated tags
      this.refreshTagifyInstance();

      // Restore focus to the tags input field
      // Bootstrap handles focus restoration, but we need to target the Tagify input
      setTimeout(() => {
        const tagifyInput = document.querySelector('.tagify__input');
        if (tagifyInput) {
          tagifyInput.focus();
        }
      }, 100);
    });

    // Handle modal before it's hidden to manage focus properly
    this.modal.addEventListener('hide.bs.modal', () => {
      // Remove focus from any focused element inside the modal
      const focusedElement = document.activeElement;
      if (focusedElement && this.modal.contains(focusedElement)) {
        focusedElement.blur();
      }
    });

    // Load all tags when modal is shown
    this.modal.addEventListener('shown.bs.modal', () => {
      // Ensure modal is properly accessible when shown
      this.modal.setAttribute('aria-hidden', 'false');
      // Load tags after a small delay to ensure modal is fully rendered
      setTimeout(() => {
        this.loadAllTags();
      }, 100);
    });

    // Handle modal when it's about to be shown
    this.modal.addEventListener('show.bs.modal', () => {
      // Ensure modal is accessible when being shown
      this.modal.setAttribute('aria-hidden', 'false');
      // Ensure initialization is complete
      if (!this.isInitialized) {
        this.setupEventListeners();
        this.isInitialized = true;
      }
      // Pre-load tags when modal starts opening
      this.loadAllTags();
    });

    // Mark listeners as setup
    this.listenersSetup = true;
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
    // Ensure preview uses tag-badge-pretty class for consistency
    if (!tagPreview.classList.contains('tag-badge-pretty')) {
      tagPreview.classList.add('tag-badge-pretty');
    }

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

    // Store current form state if editing a tag
    const currentTagId = document.getElementById('tagId')?.value;
    const currentFormData = currentTagId ? {
      name: document.getElementById('tagName')?.value || '',
      color: document.getElementById('tagColor')?.value || '',
      description: document.getElementById('tagDescription')?.value || '',
    } : null;

    try {
      const loadingDiv = document.createElement('div');
      loadingDiv.className = 'text-muted small text-center py-3';
      loadingDiv.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Loading tags...';
      container.replaceChildren(loadingDiv);

      const response = await fetch('/expenses/tags', {
        headers: {
          'X-Requested-With': 'XMLHttpRequest',
          Accept: 'application/json',
        },
        credentials: 'include', // Include cookies for authentication (required for CORS)
      });
      if (!response.ok) {
        const errorText = await response.text();
        console.error('Failed to fetch tags:', response.status, errorText);
        throw new Error(`HTTP ${response.status}: ${errorText}`);
      }

      const data = await response.json();
      console.log('Tags API response:', data);
      if (data.success && Array.isArray(data.tags)) {
        let { tags } = data;

        // Defensive check: Filter out any tags that might have inconsistent user_id
        // (This should never happen if backend is correct, but adds safety)
        const originalCount = tags.length;
        if (tags.length > 0 && tags[0].user_id !== undefined) {
          // If tags have user_id, check for consistency
          const userIds = [...new Set(tags.map((tag) => tag.user_id).filter((id) => id !== undefined))];
          if (userIds.length > 1) {
            console.error(
              `SECURITY WARNING: Received tags from multiple users: ${userIds.join(', ')}. ` +
              'This indicates a backend security issue. Filtering to first user ID.',
            );
            // Filter to the first user_id (should be current user)
            const [currentUserId] = userIds;
            tags = tags.filter((tag) => tag.user_id === currentUserId);
            console.warn(`Filtered ${originalCount - tags.length} tags from other users.`);
          }
        }

        if (tags.length !== originalCount) {
          console.warn(
            `Tag list filtered: ${originalCount} -> ${tags.length} tags. ` +
            'Some tags were removed due to user_id mismatch.',
          );
        }

        if (tags.length === 0) {
          const noTagsDiv = document.createElement('div');
          noTagsDiv.className = 'text-muted text-center py-4';
          noTagsDiv.innerHTML = '<i class="fas fa-tags fa-2x mb-2 d-block"></i><div>No tags created yet. Create your first tag above!</div>';
          container.replaceChildren(noTagsDiv);
          return;
        }

        // Create a list container for better organization
        container.replaceChildren();
        const tagList = document.createElement('div');
        tagList.className = 'tag-list-container';
        tagList.style.maxHeight = '400px';
        tagList.style.overflowY = 'auto';

        tags.forEach((tag) => {
          const tagItem = document.createElement('div');
          tagItem.className = 'tag-list-item d-flex align-items-center justify-content-between p-2 mb-2 border rounded';
          tagItem.style.cursor = 'pointer';
          tagItem.style.transition = 'background-color 0.15s ease-in-out';
          tagItem.setAttribute('data-tag-id', tag.id);

          // Hover effect
          tagItem.addEventListener('mouseenter', () => {
            tagItem.style.backgroundColor = '#f8f9fa';
          });
          tagItem.addEventListener('mouseleave', () => {
            tagItem.style.backgroundColor = '';
          });

          // Left side: Tag badge and info - align with preview section
          const tagInfo = document.createElement('div');
          tagInfo.className = 'd-flex align-items-start flex-grow-1';
          tagInfo.style.gap = '1rem';

          // Tag badge container with fixed width for consistent alignment
          const tagBadgeContainer = document.createElement('div');
          tagBadgeContainer.className = 'tag-badge-container';
          tagBadgeContainer.style.flexShrink = '0';
          tagBadgeContainer.style.width = '90px';

          // Tag badge - match preview styling exactly (compact and centered)
          const tagBadge = document.createElement('span');
          tagBadge.className = 'tag-badge tag-badge-pretty tag-editable';
          tagBadge.style.backgroundColor = tag.color;
          tagBadge.style.cursor = 'pointer';
          tagBadge.style.display = 'inline-flex';
          tagBadge.style.alignItems = 'center';
          tagBadge.style.justifyContent = 'center';
          tagBadge.style.textAlign = 'center';
          tagBadge.textContent = tag.name;

          // Adjust text color based on background brightness
          const rgb = this.hexToRgb(tag.color);
          if (rgb) {
            const brightness = (rgb.r * 299 + rgb.g * 587 + rgb.b * 114) / 1000;
            tagBadge.style.color = brightness > 128 ? '#000' : '#fff';
          }

          tagBadgeContainer.appendChild(tagBadge);
          tagInfo.appendChild(tagBadgeContainer);

          // Tag details - consistent spacing for name, description, expense totals
          const tagDetails = document.createElement('div');
          tagDetails.className = 'd-flex flex-column flex-grow-1';
          tagDetails.style.gap = '0.25rem';

          // Tag name (if different from badge display)
          const tagNameText = document.createElement('div');
          tagNameText.className = 'fw-semibold';
          tagNameText.textContent = tag.name;
          tagDetails.appendChild(tagNameText);

          // Description (if provided)
          if (tag.description && tag.description.trim()) {
            const tagDescription = document.createElement('div');
            tagDescription.className = 'text-muted small';
            tagDescription.textContent = tag.description;
            tagDetails.appendChild(tagDescription);
          }

          // Expense count (always show if available)
          if (tag.expense_count !== undefined && tag.expense_count !== null) {
            const tagExpenseCount = document.createElement('div');
            tagExpenseCount.className = 'text-muted small d-flex align-items-center';

            // Create icon element
            const icon = document.createElement('i');
            icon.className = 'fas fa-receipt me-1';

            // Create text node with expense count
            const expenseText = tag.expense_count === 1 ? 'expense' : 'expenses';
            const countText = document.createTextNode(`${tag.expense_count} ${expenseText}`);

            tagExpenseCount.appendChild(icon);
            tagExpenseCount.appendChild(countText);
            tagDetails.appendChild(tagExpenseCount);
          }

          tagInfo.appendChild(tagDetails);
          tagItem.appendChild(tagInfo);

          // Right side: Edit button
          const editButton = document.createElement('button');
          editButton.className = 'btn btn-sm btn-outline-primary';
          editButton.innerHTML = '<i class="fas fa-edit me-1"></i>Edit';
          editButton.type = 'button';
          editButton.addEventListener('click', (e) => {
            e.stopPropagation();
            this.editTag(tag.id, tag.name, tag.color, tag.description || '');
          });

          tagItem.appendChild(editButton);

          // Click handler for entire item
          tagItem.addEventListener('click', (e) => {
            // Don't trigger if clicking the edit button
            if (!e.target.closest('button')) {
              this.editTag(tag.id, tag.name, tag.color, tag.description || '');
            }
          });

          tagList.appendChild(tagItem);
        });

        container.appendChild(tagList);

        // Restore form state if we were editing a tag
        if (currentFormData && currentTagId) {
          const updatedTag = tags.find((tag) => tag.id === currentTagId);
          if (updatedTag) {
            // Use the updated tag data from the server
            this.editTag(updatedTag.id, updatedTag.name, updatedTag.color, updatedTag.description || '');
          } else {
            // Restore the form with the current form data
            document.getElementById('tagId').value = currentTagId;
            document.getElementById('tagName').value = currentFormData.name;
            document.getElementById('tagColor').value = currentFormData.color;
            document.getElementById('tagDescription').value = currentFormData.description;
            this.updateTagPreview();
          }
        }
      } else {
        const errorDiv = document.createElement('div');
        errorDiv.className = 'text-danger small';
        errorDiv.textContent = data.message || 'Failed to load tags.';
        container.replaceChildren(errorDiv);
      }
    } catch (error) {
      console.error('Error loading all tags:', error);
      const errorDiv = document.createElement('div');
      errorDiv.className = 'text-danger small';
      errorDiv.textContent = 'Error loading tags. Please try again.';
      container.replaceChildren(errorDiv);
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

    // Debug: Check if description field exists and has value
    const descriptionField = document.getElementById('tagDescription');
    console.log('Description field element:', descriptionField);
    console.log('Description field value:', tagDescription);
    console.log('Description field value length:', tagDescription?.length);

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
      console.log('Form data JSON:', JSON.stringify(formData));

      let response;
      if (tagId) {
        // Update existing tag
        response = await fetch(`/expenses/tags/${tagId}`, {
          method: 'PUT',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': document.querySelector('input[name="csrf_token"]')?.value || '',
            'X-Requested-With': 'XMLHttpRequest',
            Accept: 'application/json',
          },
          credentials: 'include', // Include cookies for authentication (required for CORS)
          body: JSON.stringify(formData),
        });
      } else {
        // Create new tag
        response = await fetch('/expenses/tags', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': document.querySelector('input[name="csrf_token"]')?.value || '',
            'X-Requested-With': 'XMLHttpRequest',
            Accept: 'application/json',
          },
          credentials: 'include', // Include cookies for authentication (required for CORS)
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

        // Don't reset form immediately - let user see the updated values
        // The form will be reset when the modal is closed

        // Trigger custom event for other components to listen to
        document.dispatchEvent(new CustomEvent('tagsUpdated', {
          detail: { tagId, tag: result.tag },
        }));

        // Update Tagify instance if it exists
        if (window.tagifyInstance) {
          // Refresh the entire Tagify instance
          this.refreshTagifyInstance();
        }
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

    // Verify tag ID is valid (numeric)
    const tagIdNum = parseInt(tagId, 10);
    if (isNaN(tagIdNum) || tagIdNum <= 0) {
      alert('Invalid tag ID. Please select a tag to delete.');
      this.resetForm();
      await this.loadAllTags();
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
          'X-Requested-With': 'XMLHttpRequest',
          Accept: 'application/json',
          'Content-Type': 'application/json',
        },
        credentials: 'include', // Include cookies for authentication (required for CORS)
      });

      // Check if response is JSON before parsing
      const contentType = response.headers.get('content-type');
      if (!contentType || !contentType.includes('application/json')) {
        const text = await response.text();
        throw new Error(`Server returned non-JSON response: ${text.substring(0, 100)}`);
      }

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

        // Update Tagify instance if it exists
        if (window.tagifyInstance) {
          // Refresh the entire Tagify instance
          this.refreshTagifyInstance();
        }
      } else {
        // Handle specific error codes
        if (response.status === 404) {
          // Tag not found - likely deleted already, refresh the list
          console.warn(`Tag ${tagId} not found, refreshing tag list`);
          await this.loadAllTags();
          alert(result.message || 'Tag not found. The tag list has been refreshed.');
        } else if (response.status === 403) {
          // Permission denied - tag belongs to another user
          console.error(`Permission denied to delete tag ${tagId}`);
          alert(result.message || 'You do not have permission to delete this tag.');
          // Refresh the list to remove any tags that shouldn't be visible
          await this.loadAllTags();
        } else {
          alert(`Error: ${result.message || 'Failed to delete tag'}`);
        }
      }
    } catch (error) {
      console.error('Error deleting tag:', error);
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';

      // If it's a 404, refresh the list
      if (errorMessage.includes('404') || errorMessage.includes('not found')) {
        console.warn('Tag not found during delete, refreshing tag list');
        await this.loadAllTags();
        alert('Tag not found. The tag list has been refreshed.');
      } else {
        alert(`Error deleting tag: ${errorMessage}`);
      }
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
   * Update Tagify whitelist with current tags
   */
  async updateTagifyWhitelist() {
    if (!window.tagifyInstance) return;

    try {
      const response = await fetch('/expenses/tags', {
        headers: {
          'X-Requested-With': 'XMLHttpRequest',
          Accept: 'application/json',
        },
        credentials: 'include', // Include cookies for authentication (required for CORS)
      });
      if (!response.ok) return;

      // Check if response is JSON before parsing
      const contentType = response.headers.get('content-type');
      if (!contentType || !contentType.includes('application/json')) {
        return;
      }

      const data = await response.json();
      if (data.success && data.tags) {
        const { tagifyInstance } = window;
        if (tagifyInstance) {
          tagifyInstance.settings.whitelist = data.tags.map((tag) => ({
            value: tag.name,
            id: tag.id,
            title: tag.description || tag.name,
            description: tag.description || '',
            color: tag.color,
          }));
        }
      }
    } catch (error) {
      console.error('Error updating Tagify whitelist:', error);
    }
  }

  /**
   * Refresh the Tagify instance to show updated tags
   */
  async refreshTagifyInstance() {
    if (!window.tagifyInstance) return;

    try {
      // Update the whitelist with latest tags
      await this.updateTagifyWhitelist();

      // Re-apply colors to existing tags - only set CSS variable
      setTimeout(() => {
        const tagElements = document.querySelectorAll('.tagify__tag[data-tag-color]');
        tagElements.forEach((tagEl) => {
          const tagColor = tagEl.getAttribute('data-tag-color');
          if (tagColor) {
            // Only set CSS variable - CSS handles the rest
            tagEl.style.setProperty('--tag-color', tagColor);
          }
        });
      }, 100);
    } catch (error) {
      console.error('Error refreshing Tagify instance:', error);
    }
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
