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
   * Initialize the tag manager (modal mode or page mode when form exists without modal).
   */
  init() {
    this.modal = document.getElementById('tagEditorModal');
    this.form = document.getElementById('tagEditorForm');

    if (this.isInitialized && this.form && document.contains(this.form)) {
      return;
    }
    if (this.form && !document.contains(this.form)) {
      this.isInitialized = false;
      this.listenersSetup = false;
    }

    if (!this.form) {
      if (!this.modal) {
        console.warn('Tag manager form not found in DOM. Will retry when modal is opened.');
      }
      const checkForm = () => {
        this.modal = document.getElementById('tagEditorModal');
        this.form = document.getElementById('tagEditorForm');
        if (this.form && !this.listenersSetup) {
          this.setupEventListeners();
          this.isInitialized = true;
          if (!this.modal) {
            this.loadAllTags();
          }
        }
      };
      let attempts = 0;
      const interval = setInterval(() => {
        attempts++;
        checkForm();
        if ((this.form && this.isInitialized) || attempts > 10) {
          clearInterval(interval);
        }
      }, 100);
      return;
    }

    this.setupEventListeners();
    this.isInitialized = true;
    if (!this.modal) {
      this.loadAllTags();
    }
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

    // New Tag button - clear form and start fresh
    const newTagBtn = document.getElementById('newTagBtn');
    if (newTagBtn) {
      newTagBtn.addEventListener('click', () => {
        this.resetForm();
        // Focus on tag name input for better UX
        const tagNameInput = document.getElementById('tagName');
        if (tagNameInput) {
          setTimeout(() => tagNameInput.focus(), 100);
        }
      });
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

    if (!this.modal) {
      this.listenersSetup = true;
      return;
    }

    // Reset modal when hidden and restore focus
    // Refresh tag selector when modal closes
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

      // Refresh Tom Select instance with latest tags (preserves currently selected tags)
      // This ensures new/edited/deleted tags are reflected in the expense form
      // Add a small delay to ensure any pending saves are complete
      setTimeout(() => {
        if (window.tagSelectInstance && typeof refreshTagSelectInstance === 'function') {
          refreshTagSelectInstance();
        }
      }, 300);

      // Restore focus to the tags input field
      setTimeout(() => {
        const tagsInput = document.getElementById('tagsInput');
        if (tagsInput && window.tagSelectInstance) {
          window.tagSelectInstance.focus();
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
     * Update the tag preview with rounded edges (matching expense details)
     */
  updateTagPreview() {
    const tagName = document.getElementById('tagName')?.value || 'Tag Preview';
    const tagColor = document.getElementById('tagColor')?.value || '#6c757d';
    const tagPreview = document.getElementById('tagPreview');

    if (!tagPreview) return;

    tagPreview.textContent = tagName;

    // Ensure preview uses tag-badge-pretty class for rounded edges (matching card badges)
    tagPreview.className = 'tag-badge tag-badge-pretty';
    tagPreview.setAttribute('data-tag-color', tagColor);

    // Set background color with !important to override any default styles
    tagPreview.style.setProperty('background-color', tagColor, 'important');

    // Set rounded edges explicitly to match card badges
    tagPreview.style.setProperty('border-radius', '20px', 'important');
    tagPreview.style.setProperty('padding', '4px 12px', 'important');
    tagPreview.style.setProperty('font-size', '0.8rem', 'important');
    tagPreview.style.setProperty('font-weight', '500', 'important');
    tagPreview.style.setProperty('box-shadow', '0 2px 4px rgba(0, 0, 0, 0.1)', 'important');
    tagPreview.style.setProperty('display', 'inline-flex', 'important');
    tagPreview.style.setProperty('align-items', 'center', 'important');
    tagPreview.style.setProperty('line-height', '1.2', 'important');
    tagPreview.style.setProperty('border', 'none', 'important');
    tagPreview.style.setProperty('margin', '2px', 'important');

    // Adjust text color based on background brightness
    const rgb = this.hexToRgb(tagColor);
    if (rgb) {
      const brightness = (rgb.r * 299 + rgb.g * 587 + rgb.b * 114) / 1000;
      const textColor = brightness > 128 ? '#000' : '#fff';
      tagPreview.style.setProperty('color', textColor, 'important');
    } else {
      tagPreview.style.setProperty('color', '#fff', 'important');
    }
  }

  /**
   * Escape HTML to prevent XSS
   */
  escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
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

      // Add cache-busting parameter to ensure fresh data after deletions
      const cacheBuster = `?t=${Date.now()}`;
      const response = await fetch(`/expenses/tags${cacheBuster}`, {
        method: 'GET',
        headers: {
          'X-Requested-With': 'XMLHttpRequest',
          Accept: 'application/json',
          'Cache-Control': 'no-cache, no-store, must-revalidate',
          Pragma: 'no-cache',
        },
        credentials: 'include', // Include cookies for authentication (required for CORS)
        cache: 'no-store', // Prevent browser caching
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
          document.dispatchEvent(new CustomEvent('tagsLoaded', { detail: { tags: [] } }));
          return;
        }

        // Create a container for tag cards (mobile-friendly, stacks vertically)
        container.replaceChildren();
        const tagGrid = document.createElement('div');
        tagGrid.className = 'tag-manager-grid';
        tagGrid.style.maxHeight = '500px';
        tagGrid.style.overflowY = 'auto';
        tagGrid.style.padding = '0.25rem';

        tags.forEach((tag) => {
          // Create a card-like container for each tag with stats
          const tagCard = document.createElement('div');
          tagCard.className = 'tag-manager-card border rounded p-3 mb-3';
          tagCard.setAttribute('data-tag-id', tag.id);
          tagCard.style.cursor = 'pointer';
          tagCard.style.transition = 'all 0.2s ease';
          tagCard.style.backgroundColor = '#fff';

          // Hover effect
          tagCard.addEventListener('mouseenter', () => {
            tagCard.style.backgroundColor = '#f8f9fa';
            tagCard.style.boxShadow = '0 2px 4px rgb(0 0 0 / 10%)';
          });
          tagCard.addEventListener('mouseleave', () => {
            tagCard.style.backgroundColor = '#fff';
            tagCard.style.boxShadow = 'none';
          });

          // Click to edit
          tagCard.addEventListener('click', () => {
            this.editTag(tag.id, tag.name, tag.color, tag.description || '');
          });

          // Top row: Tag badge (left) and action buttons (right)
          const topRow = document.createElement('div');
          topRow.className = 'd-flex justify-content-between align-items-start mb-2';

          // Left: Tag badge
          const badgeContainer = document.createElement('div');
          badgeContainer.className = 'flex-grow-1';

          const tagBadge = document.createElement('span');
          tagBadge.className = `tag-badge tag-badge-pretty tag-${tag.id}`;
          tagBadge.setAttribute('data-tag-color', tag.color);
          tagBadge.setAttribute('data-tag-id', tag.id);
          tagBadge.textContent = tag.name;

          // Set background color and text color
          tagBadge.style.backgroundColor = tag.color;
          const rgb = this.hexToRgb(tag.color);
          if (rgb) {
            const brightness = (rgb.r * 299 + rgb.g * 587 + rgb.b * 114) / 1000;
            tagBadge.style.color = brightness > 128 ? '#000' : '#fff';
          }

          badgeContainer.appendChild(tagBadge);
          topRow.appendChild(badgeContainer);

          // Right: Action buttons (right-justified)
          const actionGroup = document.createElement('div');
          actionGroup.className = 'd-flex gap-1 flex-shrink-0';
          actionGroup.style.marginLeft = 'auto'; // Ensure buttons stay on the right
          actionGroup.addEventListener('click', (e) => e.stopPropagation());

          // Edit button
          const editBtn = document.createElement('button');
          editBtn.className = 'btn btn-sm btn-outline-primary';
          editBtn.innerHTML = '<i class="fas fa-edit"></i>';
          editBtn.type = 'button';
          editBtn.title = 'Edit tag';
          editBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            this.editTag(tag.id, tag.name, tag.color, tag.description || '');
          });

          // Delete button (on same row, to the right of edit)
          const deleteBtn = document.createElement('button');
          deleteBtn.className = 'btn btn-sm btn-outline-danger';
          deleteBtn.innerHTML = '<i class="fas fa-trash"></i>';
          deleteBtn.type = 'button';
          deleteBtn.title = 'Delete tag';
          deleteBtn.addEventListener('click', async(e) => {
            e.stopPropagation();
            const confirmed = await this.confirmTagDeletion(tag);
            if (confirmed) {
              document.getElementById('tagId').value = tag.id;
              await this.deleteTag();
            }
          });

          actionGroup.appendChild(editBtn);
          actionGroup.appendChild(deleteBtn);
          topRow.appendChild(actionGroup);
          tagCard.appendChild(topRow);

          // Description section (above separator)
          if (tag.description && tag.description.trim()) {
            const descDiv = document.createElement('div');
            descDiv.className = 'text-muted small mb-2';
            const icon = document.createElement('i');
            icon.className = 'fas fa-info-circle me-1';
            descDiv.appendChild(icon);
            descDiv.appendChild(document.createTextNode(this.escapeHtml(tag.description)));
            tagCard.appendChild(descDiv);
          }

          // Separator before stats
          const separator = document.createElement('hr');
          separator.className = 'my-2';
          separator.style.marginTop = '0.5rem';
          separator.style.marginBottom = '0.5rem';
          separator.style.opacity = '0.25';
          tagCard.appendChild(separator);

          // Stats row: Left-justified statistics
          const statsRow = document.createElement('div');
          statsRow.className = 'mt-2';

          // Statistics container (left-justified)
          const statsContainer = document.createElement('div');
          statsContainer.className = 'd-flex flex-column gap-1 align-items-start';

          // Expense count
          const expenseCount = tag.expense_count !== undefined && tag.expense_count !== null ? tag.expense_count : 0;
          if (expenseCount > 0) {
            const usageDiv = document.createElement('div');
            usageDiv.className = 'text-muted small d-flex align-items-center';
            const icon = document.createElement('i');
            icon.className = 'fas fa-receipt me-1';
            icon.style.width = '16px';
            usageDiv.appendChild(icon);
            const expenseText = expenseCount === 1 ? 'expense' : 'expenses';
            usageDiv.appendChild(document.createTextNode(`${expenseCount} ${expenseText}`));
            statsContainer.appendChild(usageDiv);

            // Total amount
            if (tag.total_amount !== undefined && tag.total_amount !== null && tag.total_amount > 0) {
              const amountDiv = document.createElement('div');
              amountDiv.className = 'text-muted small d-flex align-items-center';
              const amountIcon = document.createElement('i');
              amountIcon.className = 'fas fa-dollar-sign me-1';
              amountIcon.style.width = '16px';
              amountDiv.appendChild(amountIcon);
              const formattedAmount = new Intl.NumberFormat('en-US', {
                style: 'currency',
                currency: 'USD',
                minimumFractionDigits: 2,
              }).format(tag.total_amount);
              amountDiv.appendChild(document.createTextNode(`${formattedAmount} total`));
              statsContainer.appendChild(amountDiv);
            }

            // Last visit date
            if (tag.last_visit) {
              const lastVisitDiv = document.createElement('div');
              lastVisitDiv.className = 'text-muted small d-flex align-items-center';
              const dateIcon = document.createElement('i');
              dateIcon.className = 'fas fa-calendar-alt me-1';
              dateIcon.style.width = '16px';
              lastVisitDiv.appendChild(dateIcon);
              try {
                const lastVisitDate = new Date(tag.last_visit);
                const formattedDate = new Intl.DateTimeFormat('en-US', {
                  year: 'numeric',
                  month: 'short',
                  day: 'numeric',
                }).format(lastVisitDate);
                lastVisitDiv.appendChild(document.createTextNode(`Last: ${formattedDate}`));
              } catch (error) {
                console.warn('Error formatting last visit date:', error);
                lastVisitDiv.appendChild(document.createTextNode(`Last: ${tag.last_visit}`));
              }
              statsContainer.appendChild(lastVisitDiv);
            }
          } else {
            // Show "Not used yet" if no expenses
            const usageDiv = document.createElement('div');
            usageDiv.className = 'text-muted small';
            const icon = document.createElement('i');
            icon.className = 'fas fa-receipt me-1';
            usageDiv.appendChild(icon);
            usageDiv.appendChild(document.createTextNode('Not used yet'));
            statsContainer.appendChild(usageDiv);
          }

          statsRow.appendChild(statsContainer);

          tagCard.appendChild(statsRow);
          tagGrid.appendChild(tagCard);
        });

        container.appendChild(tagGrid);

        document.dispatchEvent(new CustomEvent('tagsLoaded', { detail: { tags } }));

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

    // Update form title
    const formTitle = document.getElementById('tagFormTitle');
    if (formTitle) {
      formTitle.innerHTML = '<i class="fas fa-edit me-2"></i>Edit Tag';
    }

    // Update save button text
    const saveBtnText = document.getElementById('saveBtnText');
    if (saveBtnText) {
      saveBtnText.textContent = 'Update Tag';
    }

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

        // Update Tom Select instance if it exists
        if (window.tagSelectInstance && typeof refreshTagSelectInstance === 'function') {
          refreshTagSelectInstance();
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
    const tagIdInput = document.getElementById('tagId');
    const tagId = tagIdInput?.value;

    if (!tagId) {
      console.error('Tag delete: No tag ID found in form');
      alert('No tag selected for deletion. Please select a tag first.');
      return;
    }

    // Verify tag ID is valid (numeric)
    const tagIdNum = parseInt(tagId, 10);
    if (isNaN(tagIdNum) || tagIdNum <= 0) {
      console.error(`Tag delete: Invalid tag ID: ${tagId}`);
      alert('Invalid tag ID. Please select a tag to delete.');
      this.resetForm();
      await this.loadAllTags();
      return;
    }

    // Get tag information for confirmation dialog
    // Try to find the tag in the current tag list
    const tagCard = document.querySelector(`[data-tag-id="${tagIdNum}"]`);
    let tagInfo = null;
    if (tagCard) {
      // Try to get tag info from the tag list data
      const tagName = document.getElementById('tagName')?.value;

      // Try to find expense count from the stats in the tag card
      const statsContainer = tagCard.querySelector('.d-flex.flex-column.gap-1');
      let expenseCount = 0;
      if (statsContainer) {
        const expenseText = statsContainer.textContent;
        const expenseMatch = expenseText.match(/(\d+)\s+expense/i);
        if (expenseMatch) {
          expenseCount = parseInt(expenseMatch[1], 10);
        }
      }

      tagInfo = {
        id: tagIdNum,
        name: tagName || 'Unknown',
        expense_count: expenseCount,
      };
    }

    // If we couldn't get tag info, try to fetch it from the API
    if (!tagInfo) {
      try {
        const response = await fetch('/expenses/tags', {
          method: 'GET',
          headers: {
            'X-Requested-With': 'XMLHttpRequest',
            Accept: 'application/json',
          },
          credentials: 'include',
        });
        if (response.ok) {
          const data = await response.json();
          if (data.success && Array.isArray(data.tags)) {
            tagInfo = data.tags.find((t) => t.id === tagIdNum);
          }
        }
      } catch (error) {
        console.warn('Could not fetch tag info for confirmation:', error);
      }
    }

    // Use default tag info if we still don't have it
    if (!tagInfo) {
      tagInfo = {
        id: tagIdNum,
        name: document.getElementById('tagName')?.value || 'Unknown',
        expense_count: 0,
      };
    }

    // Show confirmation dialog with expense count
    const confirmed = await this.confirmTagDeletion(tagInfo);
    if (!confirmed) {
      return;
    }

    // Get CSRF token - try multiple sources
    const csrfInput = document.querySelector('input[name="csrf_token"]');
    const csrfToken = csrfInput?.value || document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || '';

    if (!csrfToken) {
      console.error('Tag delete: CSRF token not found');
      alert('Security token not found. Please refresh the page and try again.');
      return;
    }

    console.log(`Tag delete: Attempting to delete tag ${tagIdNum}`);

    try {
      const response = await fetch(`/expenses/tags/${tagIdNum}`, {
        method: 'DELETE',
        headers: {
          'X-CSRFToken': csrfToken,
          'X-Requested-With': 'XMLHttpRequest',
          Accept: 'application/json',
          'Content-Type': 'application/json',
        },
        credentials: 'include', // Include cookies for authentication (required for CORS)
      });

      console.log(`Tag delete: Response status: ${response.status}`);

      // Check if response is JSON before parsing
      const contentType = response.headers.get('content-type');
      if (!contentType || !contentType.includes('application/json')) {
        const text = await response.text();
        console.error(`Tag delete: Non-JSON response (${contentType}):`, text.substring(0, 200));
        throw new Error(`Server returned non-JSON response: ${text.substring(0, 100)}`);
      }

      const result = await response.json();
      console.log('Tag delete: Response data:', result);

      if (result.success) {
        console.log(`Tag delete: Successfully deleted tag ${tagIdNum}`);

        // Immediately remove the tag from the DOM if it exists
        const tagCard = document.querySelector(`[data-tag-id="${tagIdNum}"]`);
        if (tagCard) {
          console.log(`Tag delete: Removing tag ${tagIdNum} from DOM`);
          tagCard.remove();
        }

        // Reload all tags to ensure consistency
        await this.loadAllTags();

        // Reset form
        this.resetForm();

        // Trigger custom event for other components to listen to
        document.dispatchEvent(new CustomEvent('tagDeleted', {
          detail: { tagId: tagIdNum },
        }));

        // Update Tom Select instance if it exists
        if (window.tagSelectInstance && typeof refreshTagSelectInstance === 'function') {
          refreshTagSelectInstance();
        }

        // Show success message
        alert('Tag deleted successfully');
      } else {
        // Handle specific error codes
        if (response.status === 404) {
          // Tag not found - likely deleted already, refresh the list
          console.warn(`Tag ${tagIdNum} not found, refreshing tag list`);
          await this.loadAllTags();
          alert(result.message || 'Tag not found. The tag list has been refreshed.');
        } else if (response.status === 403) {
          // Permission denied - tag belongs to another user
          console.error(`Permission denied to delete tag ${tagIdNum}`);
          alert(result.message || 'You do not have permission to delete this tag.');
          // Refresh the list to remove any tags that shouldn't be visible
          await this.loadAllTags();
        } else if (response.status === 401) {
          // Authentication required
          console.error('Authentication required for tag deletion');
          alert('You must be logged in to delete tags. Please refresh the page and log in again.');
        } else {
          console.error(`Tag delete failed: ${result.message || 'Unknown error'}`);
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

    // Clear the hidden tag ID field
    const tagIdInput = document.getElementById('tagId');
    if (tagIdInput) {
      tagIdInput.value = '';
    }

    // Reset form title
    const formTitle = document.getElementById('tagFormTitle');
    if (formTitle) {
      formTitle.innerHTML = '<i class="fas fa-plus me-2"></i>Create New Tag';
    }

    // Reset save button text
    const saveBtnText = document.getElementById('saveBtnText');
    if (saveBtnText) {
      saveBtnText.textContent = 'Save Tag';
    }

    // Hide delete button
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

  /**
   * Show a warning dialog before deleting a tag
   * @param {Object} tag - Tag object with id, name, expense_count, etc.
   * @returns {Promise<boolean>} - True if user confirms deletion, false otherwise
   */
  confirmTagDeletion(tag) {
    const tagNameEscaped = this.escapeHtml(tag.name);
    const expenseCount = tag.expense_count !== undefined && tag.expense_count !== null ? tag.expense_count : 0;

    // Build warning message based on expense count
    let message;
    let title;
    let alertClass = 'alert-info';
    if (expenseCount > 0) {
      const expenseText = expenseCount === 1 ? 'expense' : 'expenses';
      title = '⚠️ Warning: Tag is in Use';
      alertClass = 'alert-warning';
      message = `<p>The tag <strong>"${tagNameEscaped}"</strong> is currently associated with <strong>${expenseCount} ${expenseText}</strong>.</p>` +
        '<p>Deleting this tag will remove it from all associated expenses. This action cannot be undone.</p>';
    } else {
      title = 'Delete Tag';
      message = `<p>Are you sure you want to delete the tag <strong>"${tagNameEscaped}"</strong>?</p>` +
        '<p>This action cannot be undone.</p>';
    }

    // Create a Bootstrap modal for better UX
    return new Promise((resolve) => {
      // Check if modal already exists and remove it
      const existingModal = document.getElementById('tagDeleteConfirmModal');
      if (existingModal) {
        existingModal.remove();
      }

      // Create modal HTML
      const modalHtml = `
        <div class="modal fade" id="tagDeleteConfirmModal" tabindex="-1" aria-labelledby="tagDeleteConfirmModalLabel" aria-hidden="true">
          <div class="modal-dialog modal-dialog-centered">
            <div class="modal-content">
              <div class="modal-header ${expenseCount > 0 ? 'bg-warning' : ''}">
                <h5 class="modal-title" id="tagDeleteConfirmModalLabel">
                  <i class="fas fa-exclamation-triangle me-2"></i>${title}
                </h5>
                <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
              </div>
              <div class="modal-body">
                <div class="alert ${alertClass}" role="alert">
                  ${message}
                </div>
              </div>
              <div class="modal-footer">
                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                <button type="button" class="btn btn-danger" id="confirmDeleteTagBtn">
                  <i class="fas fa-trash me-1"></i>Delete Tag
                </button>
              </div>
            </div>
          </div>
        </div>
      `;

      // Insert modal into body
      document.body.insertAdjacentHTML('beforeend', modalHtml);

      const modalElement = document.getElementById('tagDeleteConfirmModal');
      const modal = new bootstrap.Modal(modalElement, {
        backdrop: 'static',
        keyboard: false,
      });

      // Handle confirm button
      const confirmBtn = document.getElementById('confirmDeleteTagBtn');
      confirmBtn.addEventListener('click', () => {
        modal.hide();
        resolve(true);
      });

      // Handle cancel/close
      modalElement.addEventListener('hidden.bs.modal', () => {
        modalElement.remove();
        resolve(false);
      });

      // Show modal
      modal.show();
    });
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
