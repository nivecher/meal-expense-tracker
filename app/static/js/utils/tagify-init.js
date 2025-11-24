/**
 * Tagify initialization for expense forms
 */

// Fix Tagify elements to be compatible with browser extensions
function fixTagifyElementsForExtensions() {
  // Patch all existing tag elements
  const tagElements = document.querySelectorAll('tag');
  tagElements.forEach((tag) => {
    if (!tag.tagName || typeof tag.tagName.toLowerCase !== 'function') {
      Object.defineProperty(tag, 'tagName', {
        value: 'TAG',
        writable: false,
        configurable: false,
      });

      if (!tag.tagName.toLowerCase) {
        tag.tagName.toLowerCase = function() {
          return 'tag';
        };
      }
    }
  });

  // Watch for new tag elements being added
  const observer = new MutationObserver((mutations) => {
    mutations.forEach((mutation) => {
      mutation.addedNodes.forEach((node) => {
        if (node.nodeType === Node.ELEMENT_NODE) {
          if (node.tagName === 'TAG') {
            if (!node.tagName || typeof node.tagName.toLowerCase !== 'function') {
              Object.defineProperty(node, 'tagName', {
                value: 'TAG',
                writable: false,
                configurable: false,
              });

              if (!node.tagName.toLowerCase) {
                node.tagName.toLowerCase = function() {
                  return 'tag';
                };
              }
            }
          }

          // Also check child elements
          const childTags = node.querySelectorAll && node.querySelectorAll('tag');
          if (childTags) {
            childTags.forEach((childTag) => {
              if (!childTag.tagName || typeof childTag.tagName.toLowerCase !== 'function') {
                Object.defineProperty(childTag, 'tagName', {
                  value: 'TAG',
                  writable: false,
                  configurable: false,
                });

                if (!childTag.tagName.toLowerCase) {
                  childTag.tagName.toLowerCase = function() {
                    return 'tag';
                  };
                }
              }
            });
          }
        }
      });
    });
  });

  observer.observe(document.body, {
    childList: true,
    subtree: true,
  });
}

// Initialize Tagify for expense forms
document.addEventListener('DOMContentLoaded', () => {
  const tagsInput = document.getElementById('tagsInput');
  // Prevent double initialization
  if (tagsInput && !tagsInput.tagify) {
    // Get existing tags from input value and data attribute
    const existingTagsValue = tagsInput.value;
    const existingTagsData = tagsInput.getAttribute('data-existing-tags');
    let existingTags = [];

    if (existingTagsData) {
      try {
        const parsedTags = JSON.parse(existingTagsData);
        existingTags = parsedTags.map((tag) => ({
          value: tag.name,
          id: tag.id,
          color: tag.color,
          title: tag.description || tag.name,
          description: tag.description || '',
        }));
      } catch (error) {
        console.warn('Failed to parse existing tags data:', error);
        // Fallback to simple name parsing
        existingTags = existingTagsValue ? existingTagsValue.split(',').map((tag) => tag.trim()).filter((tag) => tag) : [];
      }
    } else {
      existingTags = existingTagsValue ? existingTagsValue.split(',').map((tag) => tag.trim()).filter((tag) => tag) : [];
    }

    // Initialize Tagify
    const tagify = new Tagify(tagsInput, {
      whitelist: [],
      maxTags: 20,
      enforceWhitelist: false,
      addTagOnBlur: true,
      duplicates: false,
      trim: true,
      dropdown: {
        enabled: 1,
        closeOnSelect: false,
        highlightFirst: true,
        searchKeys: ['value', 'name'],
      },
      templates: {
        tag: (tagData) => {
          const tagId = tagData.id || tagData.value;
          const tagColor = tagData.color || '#6c757d'; // Default gray if no color
          const tagDescription = tagData.description || tagData.title || '';

          // Calculate text color based on background brightness
          const hexToRgb = (hex) => {
            const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
            return result ? {
              r: parseInt(result[1], 16),
              g: parseInt(result[2], 16),
              b: parseInt(result[3], 16),
            } : null;
          };

          const rgb = hexToRgb(tagColor);
          const brightness = rgb ? (rgb.r * 299 + rgb.g * 587 + rgb.b * 114) / 1000 : 128;
          const textColor = brightness > 128 ? '#000' : '#fff';

          return `
                        <tag title="${tagDescription}"
                             contenteditable='false'
                             spellcheck='false'
                             tabIndex="-1"
                             class="tagify__tag tagify-tag-pretty"
                             data-tagify-tag="true"
                             data-tag-id="${tagId}"
                             data-tag-color="${tagColor}"
                             data-tag-description="${tagDescription}"
                             style="--tag-color: ${tagColor}; background-color: ${tagColor} !important; background: ${tagColor} !important; background-image: none !important; color: ${textColor} !important;">
                        <x title='' class='tagify__tag__removeBtn' role='button' aria-label='remove tag'></x>
                        <div>
                            <span class='tagify__tag-text' style="color: ${textColor} !important;">${tagData.value}</span>
                        </div>
                    </tag>
                    `;
        },
      },
    });

    // Load available tags
    fetch('/expenses/tags')
      .then((response) => response.json())
      .then((data) => {
        if (data.success && data.tags) {
          tagify.settings.whitelist = data.tags.map((tag) => ({
            value: tag.name,
            id: tag.id,
            title: tag.description || tag.name,
            description: tag.description || '',
            color: tag.color,
          }));

          // Add existing tags to Tagify after whitelist is loaded
          // Only add if Tagify doesn't already have tags (prevent duplicates)
          if (existingTags.length > 0 && tagify.value.length === 0) {
            // If we have full tag data (from data-existing-tags), use it directly
            if (existingTags[0] && existingTags[0].id) {
              tagify.addTags(existingTags);
            } else {
              // Fallback: try to match with whitelist
              existingTags.forEach((tagName) => {
                const matchingTag = tagify.settings.whitelist.find((tag) => tag.value === tagName);
                const tagData = matchingTag ? {
                  value: tagName,
                  id: matchingTag.id,
                  color: matchingTag.color,
                } : { value: tagName };
                tagify.addTags([tagData]);
              });
            }
          }
        }
      })
      .catch((error) => console.error('Failed to load tags:', error));

    // CSS variable is already set in template, so no need to re-apply
    // Tagify will handle tag rendering with the styles from the template

    // Make globally available
    window.tagifyInstance = tagify;

    // Watch for Tagify tags being added/updated and ensure styles are applied
    const tagStyleObserver = new MutationObserver(() => {
      const tagElements = document.querySelectorAll('.tagify__tag[data-tag-color]');
      tagElements.forEach((tagEl) => {
        const tagColor = tagEl.getAttribute('data-tag-color');
        if (tagColor) {
          // Force apply background color with maximum specificity
          tagEl.style.setProperty('background-color', tagColor, 'important');
          tagEl.style.setProperty('background', tagColor, 'important');
          tagEl.style.setProperty('background-image', 'none', 'important');
          // Ensure text color is set based on brightness
          const textSpan = tagEl.querySelector('.tagify__tag-text');
          if (textSpan && !textSpan.style.color) {
            const hexToRgb = (hex) => {
              const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
              return result ? {
                r: parseInt(result[1], 16),
                g: parseInt(result[2], 16),
                b: parseInt(result[3], 16),
              } : null;
            };
            const rgb = hexToRgb(tagColor);
            const brightness = rgb ? (rgb.r * 299 + rgb.g * 587 + rgb.b * 114) / 1000 : 128;
            const textColor = brightness > 128 ? '#000' : '#fff';
            textSpan.style.setProperty('color', textColor, 'important');
          }
        }
      });
    });

    // Observe the Tagify container for changes
    const tagifyContainer = tagsInput.closest('.tagify') || tagsInput.parentElement;
    if (tagifyContainer) {
      tagStyleObserver.observe(tagifyContainer, {
        childList: true,
        subtree: true,
        attributes: true,
        attributeFilter: ['data-tag-color', 'class'],
      });
    }

    // Apply styles immediately to any existing tags
    setTimeout(() => {
      const tagElements = document.querySelectorAll('.tagify__tag[data-tag-color]');
      tagElements.forEach((tagEl) => {
        const tagColor = tagEl.getAttribute('data-tag-color');
        if (tagColor) {
          tagEl.style.setProperty('background-color', tagColor, 'important');
          tagEl.style.setProperty('background', tagColor, 'important');
          tagEl.style.setProperty('background-image', 'none', 'important');
        }
      });
    }, 50);

    // Fix Tagify elements for browser extensions
    setTimeout(() => {
      fixTagifyElementsForExtensions();
    }, 100);
  }

  // Ensure tag manager is initialized
  if (window.tagManager) {
    window.tagManager.init();
  }

  // Handle manage tags link click
  const manageTagsLink = document.getElementById('manageTagsLink');
  if (manageTagsLink) {
    manageTagsLink.addEventListener('click', (e) => {
      e.preventDefault();

      // Ensure tag manager is initialized before showing modal
      if (window.tagManager && window.tagManager.modal) {
        const modalInstance = new bootstrap.Modal(window.tagManager.modal);
        modalInstance.show();
      } else {
        console.warn('Tag manager not properly initialized');
      }
    });
  }
});
