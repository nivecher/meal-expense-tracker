/**
 * Tom Select initialization for expense forms and filter forms
 * Provides tag input with autocomplete, custom colors, and case preservation
 */

// Helper function to calculate text color based on background brightness
function getTextColor(backgroundColor) {
  const hexToRgb = (hex) => {
    const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
    return result ? {
      r: parseInt(result[1], 16),
      g: parseInt(result[2], 16),
      b: parseInt(result[3], 16),
    } : null;
  };

  const rgb = hexToRgb(backgroundColor);
  if (!rgb) return '#000';
  const brightness = (rgb.r * 299 + rgb.g * 587 + rgb.b * 114) / 1000;
  return brightness > 128 ? '#000' : '#fff';
}

// Initialize a single tag selector
function initializeTagSelector(inputElement, options = {}) {
  if (!inputElement) return null;

  // Prevent double initialization
  if (inputElement.tagSelect) return inputElement.tagSelect;

  // Ensure element is visible in DOM (or will be)
  if (!inputElement.parentElement) {
    console.warn('Tag selector element not in DOM yet, will retry');
    return null;
  }

  const allowCreate = options.allowCreate !== false; // Default true for expense form
  const existingTags = options.existingTags || [];
  const selectedTags = options.selectedTags || [];

  // Store all available tags for case-insensitive matching
  let allTags = [];

  // Create tagSelect variable first to reference in callbacks
  let tagSelect = null;

  // Preserve original classes for Bootstrap compatibility
  const originalClasses = inputElement.className;

  // Clear any default options or text that might show through
  // (select elements don't support placeholders, but clear any selected options)
  // This prevents any visible text from showing before Tom Select initializes
  if (inputElement.options) {
    Array.from(inputElement.options).forEach((option) => {
      option.selected = false; // Clear all selections - Tom Select will handle selected values
    });
  }

  // Also clear any innerHTML/text that might be showing
  if (inputElement.innerHTML) {
    inputElement.innerHTML = '';
  }

  // Initialize Tom Select with multi-select configuration
  const tagSelectConfig = {
    plugins: ['remove_button'],
    maxItems: null, // No limit on number of tags
    persist: false, // Don't persist to localStorage
    valueField: 'name', // Store tag names (what backend expects)
    labelField: 'name',
    searchField: ['name'],
    options: [], // Will be populated from API
    openOnFocus: true, // Open dropdown when field is focused
    closeAfterSelect: false, // Keep dropdown open after selecting (for multiple selections)
    maxOptions: null, // Show all available options (no limit)
    loadThrottle: 300, // Throttle load requests
    placeholder: inputElement.getAttribute('placeholder') || 'Type to add tags...', // Use placeholder from element
    hideSelected: true, // Hide selected items from dropdown (prevents showing already-selected tags)
    load: (query, callback) => {
      // If query is empty, return all available tags from allTags array
      // This ensures users can see all tags when they open the dropdown
      if (!query || query.trim() === '') {
        if (allTags && allTags.length > 0) {
          callback(allTags);
          return;
        }
        // If allTags not loaded yet, fetch all tags from API
        fetch('/expenses/tags', {
          credentials: 'include',
        })
          .then((response) => {
            if (!response.ok) {
              return { success: false, tags: [] };
            }
            return response.json();
          })
          .then((data) => {
            if (data.success && Array.isArray(data.tags)) {
              const tags = data.tags.map((tag) => ({
                id: tag.id,
                name: tag.name,
                color: tag.color || '#6c757d',
                description: tag.description || tag.name,
              }));
              allTags = tags;
              callback(tags);
            } else {
              callback([]);
            }
          })
          .catch(() => {
            callback([]);
          });
        return;
      }

      // Case-insensitive search via API for non-empty queries
      const searchUrl = `/expenses/tags/search?q=${encodeURIComponent(query)}&limit=20`;
      fetch(searchUrl, {
        credentials: 'include',
      })
        .then((response) => {
          if (!response.ok) {
            return [];
          }
          return response.json();
        })
        .then((data) => {
          if (data.success && Array.isArray(data.tags)) {
            const options = data.tags.map((tag) => ({
              id: tag.id,
              name: tag.name,
              color: tag.color || '#6c757d',
              description: tag.description || tag.name,
            }));
            callback(options);
          } else {
            callback([]);
          }
        })
        .catch(() => {
          callback([]);
        });
    },
    render: {
      option: (data, escape) => {
        const tagColor = data.color || '#6c757d';
        const textColor = getTextColor(tagColor);
        return `
          <div class="tag-select-option" data-color="${escape(tagColor)}" style="--tag-color: ${tagColor};">
            <span class="tag-select-option-badge" style="background-color: ${tagColor}; color: ${textColor};">
              ${escape(data.name)}
            </span>
            ${data.description && data.description !== data.name ? `<span class="tag-select-option-desc">${escape(data.description)}</span>` : ''}
          </div>
        `;
      },
      item: (data, escape) => {
        const tagColor = data.color || '#6c757d';
        const textColor = getTextColor(tagColor);
        const description = data.description && data.description !== data.name ? data.description : '';
        const tooltipAttr = description ? `title="${escape(description)}" data-bs-toggle="tooltip" data-bs-placement="top"` : '';
        return `
          <div class="tag-select-item" data-color="${escape(tagColor)}" data-tag-id="${data.id || ''}" data-tag-description="${escape(description)}" style="--tag-color: ${tagColor};" ${tooltipAttr}>
            <span class="tag-select-item-badge" style="background-color: ${tagColor}; color: ${textColor};">
              ${escape(data.name)}
            </span>
          </div>
        `;
      },
      no_results: () => {
        if (allowCreate) {
          return '<div class="no-results">No tags found. Type to create a new tag.</div>';
        }
        return '<div class="no-results">No tags found.</div>';
      },
    },
    onInitialize: () => {
      // Load all tags for case-insensitive matching
      fetch('/expenses/tags', {
        credentials: 'include',
      })
        .then((response) => {
          if (!response.ok) {
            return { success: false, tags: [] };
          }
          const contentType = response.headers.get('content-type');
          if (!contentType || !contentType.includes('application/json')) {
            return { success: false, tags: [] };
          }
          return response.json();
        })
        .then((data) => {
          if (data.success && Array.isArray(data.tags)) {
            allTags = data.tags.map((tag) => ({
              id: tag.id,
              name: tag.name,
              color: tag.color || '#6c757d',
              description: tag.description || tag.name,
            }));

            // Add all tags as options for autocomplete
            if (tagSelect) {
              tagSelect.addOptions(allTags);
              // Refresh options to ensure they're available for display
              tagSelect.refreshOptions(false);

              // Add existing tags if available (for expense form editing)
              if (existingTags.length > 0) {
                const tagsToAdd = existingTags.map((existingTag) => {
                  const matchingTag = allTags.find(
                    (tag) => tag.id === existingTag.id || tag.name.toLowerCase() === existingTag.name.toLowerCase(),
                  );
                  return matchingTag || existingTag;
                });

                tagsToAdd.forEach((tag) => {
                  if (!tagSelect.options[tag.name]) {
                    tagSelect.addOption(tag);
                  }
                  tagSelect.addItem(tag.name, true); // true = silent
                });

                // Initialize tooltips for existing tags after they're added
                setTimeout(() => {
                  const tagItems = inputElement.parentElement.querySelectorAll('.tag-select-item[data-bs-toggle="tooltip"]');
                  tagItems.forEach((item) => {
                    const existingTooltip = bootstrap.Tooltip.getInstance(item);
                    if (existingTooltip) {
                      existingTooltip.dispose();
                    }
                    if (item.getAttribute('data-tag-description')) {
                      new bootstrap.Tooltip(item, { placement: 'top' }); // eslint-disable-line no-new
                    }
                  });
                }, 200);
              }

              // Add selected tags if available (for filter form)
              if (selectedTags.length > 0) {
                const tagsToAdd = selectedTags.map((tagName) => {
                  const matchingTag = allTags.find(
                    (tag) => tag.name.toLowerCase() === tagName.toLowerCase(),
                  );
                  return matchingTag || { id: tagName, name: tagName, color: '#6c757d', description: tagName };
                });

                tagsToAdd.forEach((tag) => {
                  if (!tagSelect.options[tag.name]) {
                    tagSelect.addOption(tag);
                  }
                  tagSelect.addItem(tag.name, true); // true = silent
                });

                // Initialize tooltips for selected tags
                setTimeout(() => {
                  const tagItems = inputElement.parentElement.querySelectorAll('.tag-select-item[data-bs-toggle="tooltip"]');
                  tagItems.forEach((item) => {
                    const existingTooltip = bootstrap.Tooltip.getInstance(item);
                    if (existingTooltip) {
                      existingTooltip.dispose();
                    }
                    if (item.getAttribute('data-tag-description')) {
                      new bootstrap.Tooltip(item, { placement: 'top' }); // eslint-disable-line no-new
                    }
                  });
                }, 200);
              }
            }
          }
        })
        .catch((error) => {
          console.error('Failed to load tags:', error);
        });
    },
    onItemAdd: (_value) => {
      // Preserve user's case - no case normalization
      // Initialize tooltip for newly added tag item
      setTimeout(() => {
        if (tagSelect && tagSelect.control) {
          const tagItems = tagSelect.control.querySelectorAll('.tag-select-item[data-bs-toggle="tooltip"]');
          tagItems.forEach((item) => {
            const existingTooltip = bootstrap.Tooltip.getInstance(item);
            if (existingTooltip) {
              existingTooltip.dispose();
            }
            if (item.getAttribute('data-tag-description')) {
              new bootstrap.Tooltip(item, { placement: 'top' }); // eslint-disable-line no-new
            }
          });
        }
      }, 100);
    },
    onFocus: () => {
      // When focused, trigger load to show all tags in dropdown
      if (tagSelect) {
        // If allTags not loaded yet, load them
        if (allTags.length === 0) {
          tagSelect.load('', (options) => {
            if (options && options.length > 0) {
              allTags = options;
              tagSelect.addOptions(options);
              tagSelect.refreshOptions(false);
            }
          });
        } else {
          // Tags already loaded, just refresh options
          tagSelect.refreshOptions(false);
        }
      }
    },
  };

  // Only allow creating new tags if allowCreate is true
  if (allowCreate) {
    tagSelectConfig.create = (input, callback) => {
      const tagName = input.trim();
      if (!tagName) {
        callback(null);
        return;
      }
      const newTag = {
        id: tagName,
        name: tagName,
        color: '#6c757d',
        description: tagName,
      };
      callback(newTag);
    };
  }

  try {
    tagSelect = new TomSelect(inputElement, tagSelectConfig);

    // Verify Tom Select initialized correctly
    if (!tagSelect || !tagSelect.wrapper) {
      console.error('Tom Select failed to initialize for element:', inputElement.id);
      return null;
    }

    // Store instance
    inputElement.tagSelect = tagSelect;

    // IMMEDIATELY hide the original select element completely
    // Tom Select wraps the select, but we need to hide it completely
    if (inputElement) {
      // Force hide immediately with inline styles
      inputElement.classList.add('ts-hidden');
      inputElement.setAttribute('aria-hidden', 'true');
      inputElement.setAttribute('tabindex', '-1');

      // Apply all hiding styles immediately
      const hideStyles = {
        display: 'none',
        visibility: 'hidden',
        position: 'absolute',
        opacity: '0',
        pointerEvents: 'none',
        height: '0',
        width: '0',
        maxHeight: '0',
        maxWidth: '0',
        overflow: 'hidden',
        margin: '0',
        padding: '0',
        border: 'none',
        lineHeight: '0',
        fontSize: '0',
      };

      Object.assign(inputElement.style, hideStyles);
    }

    // Ensure Bootstrap 5 styling is applied correctly
    // Copy form-control class from original select to Tom Select control for consistent styling
    if (tagSelect.control && originalClasses.includes('form-control')) {
      // The Tom Select Bootstrap 5 theme should add form-control, but ensure it's there
      if (!tagSelect.control.classList.contains('form-control')) {
        tagSelect.control.classList.add('form-control');
      }
    }

    // Ensure wrapper and control take full width and proper display
    if (tagSelect.wrapper) {
      // Make sure wrapper is positioned correctly - it should replace the select visually
      tagSelect.wrapper.style.width = '100%';
      tagSelect.wrapper.style.display = 'block';
      tagSelect.wrapper.style.position = 'relative';
      tagSelect.wrapper.style.margin = '0';
      tagSelect.wrapper.style.padding = '0';
      tagSelect.wrapper.style.verticalAlign = 'top';

      if (tagSelect.control) {
        tagSelect.control.style.width = '100%';
        tagSelect.control.style.display = 'flex';
        tagSelect.control.style.flexWrap = 'wrap';
        tagSelect.control.style.alignItems = 'center';
        tagSelect.control.style.overflow = 'visible';
        tagSelect.control.style.maxHeight = 'none';
        tagSelect.control.style.cursor = 'text';
        tagSelect.control.style.minHeight = '6rem';
      }

      // Ensure input field is focusable, clickable, and styled correctly
      const controlInput = tagSelect.control_input;
      if (controlInput) {
        controlInput.style.pointerEvents = 'auto';
        controlInput.style.cursor = 'text';
        controlInput.style.zIndex = '1';
        controlInput.style.color = '#212529'; // Bootstrap default text color
        controlInput.style.backgroundColor = 'transparent';

        // Set proper placeholder
        const placeholderText = tagSelectConfig.placeholder || (allowCreate ? 'Type to add tags...' : 'Type to search tags...');
        controlInput.placeholder = placeholderText;

        // Remove any weird text that might be showing (like "Type 1")
        const currentValue = controlInput.value ? controlInput.value.trim() : '';
        if (currentValue && (currentValue.toLowerCase().includes('type') || currentValue.length < 2)) {
          controlInput.value = '';
        }

        // Ensure input type is correct (should be text, not hidden)
        if (controlInput.type === 'hidden') {
          controlInput.type = 'text';
        }
      }

      // Hide any input-sizer, hidden-placeholder, or other helper elements
      const helperElements = tagSelect.wrapper.querySelectorAll('.input-sizer, .ts-hidden-placeholder, input-sizer');
      helperElements.forEach((el) => {
        el.style.display = 'none';
        el.style.visibility = 'hidden';
        el.style.position = 'absolute';
        el.style.opacity = '0';
        el.style.height = '0';
        el.style.width = '0';
      });

      // Ensure control-items (where tags are displayed) wrap horizontally
      const controlItems = tagSelect.control?.querySelector('.ts-control-items');
      if (controlItems) {
        controlItems.style.display = 'flex';
        controlItems.style.flexWrap = 'wrap';
        controlItems.style.alignItems = 'center';
        controlItems.style.gap = '0.125rem';
        controlItems.style.width = '100%';
      }
    }

    // Ensure the control can receive focus and clicks
    if (tagSelect.control) {
      tagSelect.control.setAttribute('tabindex', '-1'); // Allow focus but not tab navigation
      tagSelect.control.style.cursor = 'text';
    }

    // Final check: ensure original select is completely hidden after initialization
    // Use multiple timeouts to catch any re-rendering
    const hideSelectCompletely = () => {
      if (!inputElement) return;

      // Apply all hiding methods
      inputElement.classList.add('ts-hidden');
      inputElement.setAttribute('aria-hidden', 'true');
      inputElement.setAttribute('tabindex', '-1');

      const hideStyles = {
        display: 'none',
        visibility: 'hidden',
        position: 'absolute',
        opacity: '0',
        pointerEvents: 'none',
        height: '0',
        width: '0',
        maxHeight: '0',
        maxWidth: '0',
        overflow: 'hidden',
        margin: '0',
        padding: '0',
        border: 'none',
        lineHeight: '0',
        fontSize: '0',
        top: '-9999px',
        left: '-9999px',
      };
      Object.assign(inputElement.style, hideStyles);

      // Also hide via CSS class
      if (!inputElement.classList.contains('ts-hidden')) {
        inputElement.classList.add('ts-hidden');
      }

      // Hide any helper elements
      if (tagSelect.wrapper) {
        const helpers = tagSelect.wrapper.querySelectorAll('.input-sizer, .ts-hidden-placeholder, [class*="sizer"]');
        helpers.forEach((el) => {
          el.style.display = 'none';
          el.style.visibility = 'hidden';
          el.style.position = 'absolute';
          el.style.opacity = '0';
          el.style.height = '0';
          el.style.width = '0';
        });
      }

      // Ensure wrapper is visible and properly positioned
      if (tagSelect.wrapper) {
        tagSelect.wrapper.style.display = 'block';
        tagSelect.wrapper.style.visibility = 'visible';
        tagSelect.wrapper.style.opacity = '1';
      }

      // Remove any "Type 1" or similar placeholder text artifacts
      if (tagSelect.control_input) {
        // Clear any weird text values
        if (tagSelect.control_input.value && tagSelect.control_input.value.includes('Type')) {
          tagSelect.control_input.value = '';
        }
        // Ensure placeholder is set correctly
        tagSelect.control_input.placeholder = tagSelectConfig.placeholder || '';
      }
    };

    // Hide immediately and again after brief delays to catch any re-rendering
    hideSelectCompletely();
    setTimeout(hideSelectCompletely, 0);
    setTimeout(hideSelectCompletely, 50);
    setTimeout(hideSelectCompletely, 100);
    setTimeout(hideSelectCompletely, 200);

    // Use MutationObserver to watch for any changes that might show the select again
    if (typeof MutationObserver !== 'undefined' && inputElement.parentElement) {
      const observer = new MutationObserver(() => {
        if (inputElement && inputElement.style.display !== 'none') {
          hideSelectCompletely();
        }
      });

      observer.observe(inputElement.parentElement, {
        attributes: true,
        attributeFilter: ['style', 'class'],
        childList: true,
        subtree: true,
      });

      // Store observer on tagSelect instance for potential cleanup
      if (tagSelect) {
        tagSelect.tsObserver = observer;
      }
    }

    return tagSelect;
  } catch (error) {
    console.error('Error initializing Tom Select:', error);
    return null;
  }
}

// Make initializeTagSelector available globally for late initialization
window.initializeTagSelector = initializeTagSelector;

document.addEventListener('DOMContentLoaded', () => {
  // Check if TomSelect is available
  if (typeof TomSelect === 'undefined') {
    console.error('TomSelect library is not loaded. Make sure tom-select.complete.min.js is included before this script.');
    return;
  }

  // Initialize expense form tag selector (tagsInput)
  const tagsInput = document.getElementById('tagsInput');
  if (tagsInput) {
    // Get existing tags from data attribute (for editing expenses)
    const existingTagsData = tagsInput.getAttribute('data-existing-tags');
    let existingTags = [];

    if (existingTagsData) {
      try {
        // getAttribute() already decodes HTML entities, so we can parse JSON directly
        // This is safe because the data comes from server-side JSON encoding
        const parsedTags = JSON.parse(existingTagsData);
        existingTags = parsedTags.map((tag) => ({
          id: tag.id,
          name: tag.name,
          color: tag.color || '#6c757d',
          description: tag.description || tag.name,
        }));
      } catch (error) {
        console.error('Failed to parse existing tags data:', error);
      }
    }

    const tagSelect = initializeTagSelector(tagsInput, {
      allowCreate: true,
      existingTags,
    });

    if (tagSelect) {
      // Store instance globally for tag manager integration
      window.tagSelectInstance = tagSelect;

      // Ensure tag manager is initialized
      if (window.tagManager) {
        window.tagManager.init();
      }

      // Handle manage tags link click
      const manageTagsLink = document.getElementById('manageTagsLink');
      if (manageTagsLink) {
        manageTagsLink.addEventListener('click', (e) => {
          e.preventDefault();

          if (window.tagManager && window.tagManager.modal) {
            const modalInstance = new bootstrap.Modal(window.tagManager.modal);
            modalInstance.show();
          } else {
            console.warn('Tag manager not properly initialized');
          }
        });
      }
    }
  }

  // Note: filterTagsInput initialization is handled by expense-list.js
  // to avoid duplicate initialization and ensure proper timing
});
