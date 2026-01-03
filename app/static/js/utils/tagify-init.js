/**
 * Tagify initialization for expense forms
 */

// Comprehensive fix for tagName.toLowerCase errors from browser extensions
// This ensures all elements have a proper tagName property that's a string
function applyTagNameWrapper(element, currentTagName, upperTagName) {
  // Try to create a wrapper that ensures tagName is always a string
  const originalTagName = currentTagName || upperTagName;
  try {
    Object.defineProperty(element, 'tagName', {
      get() {
        const tagName = originalTagName || (element.localName || element.nodeName || 'UNKNOWN').toUpperCase();
        return typeof tagName === 'string' ? tagName : String(tagName).toUpperCase();
      },
      configurable: true,
      enumerable: false,
    });
  } catch (_wrapError) {
    // If all else fails, just log and continue
    console.debug('Could not fix tagName for element:', _wrapError);
  }
}

function fixElementTagName(element) {
  if (!element || element.nodeType !== Node.ELEMENT_NODE) {
    return;
  }

  try {
    // Get the actual tag name (handles custom elements)
    const actualTagName = element.localName || element.nodeName || 'UNKNOWN';
    const upperTagName = typeof actualTagName === 'string' ? actualTagName.toUpperCase() : 'UNKNOWN';

    // Check if tagName is missing, not a string, or doesn't have toLowerCase
    const currentTagName = element.tagName;
    const needsFix = !currentTagName ||
      typeof currentTagName !== 'string' ||
      typeof currentTagName.toLowerCase !== 'function';

    if (needsFix) {
      // Try to get the original tagName descriptor
      let descriptor = Object.getOwnPropertyDescriptor(element, 'tagName');
      if (!descriptor) {
        // Try parent prototype
        const proto = Object.getPrototypeOf(element);
        if (proto) {
          descriptor = Object.getOwnPropertyDescriptor(proto, 'tagName');
        }
      }

      // Only try to fix if configurable or if we can't determine
      if (!descriptor || descriptor.configurable !== false) {
        try {
          // Replace with a string value
          Object.defineProperty(element, 'tagName', {
            value: upperTagName,
            writable: false,
            configurable: true,
            enumerable: false,
          });
        } catch (_defineError) {
          // Try fallback wrapper approach
          applyTagNameWrapper(element, currentTagName, upperTagName);
        }
      }
    }
  } catch (error) {
    // Silently handle errors (e.g., if element is not configurable)
    console.debug('Error fixing element tagName:', error);
  }
}

// Fix elements to be compatible with browser extensions
// This ensures all elements have proper tagName properties
function fixTagifyElementsForExtensions() {
  // Patch all existing elements (especially custom elements like <tag>)
  try {
    const allElements = document.querySelectorAll('*');
    allElements.forEach((el) => {
      fixElementTagName(el);
    });
  } catch (error) {
    // Silently handle errors (e.g., from browser extensions)
    console.debug('Error fixing existing elements:', error);
  }

  // Watch for new elements being added and fix them
  if (!document.body) {
    return; // Body not ready yet
  }

  const observer = new MutationObserver((mutations) => {
    mutations.forEach((mutation) => {
      mutation.addedNodes.forEach((node) => {
        if (node.nodeType === Node.ELEMENT_NODE) {
          // Fix the node itself
          fixElementTagName(node);

          // Fix all child elements (including custom elements)
          if (node.querySelectorAll) {
            try {
              const allElements = node.querySelectorAll('*');
              allElements.forEach((el) => {
                fixElementTagName(el);
              });
            } catch (error) {
              // Silently handle errors from browser extensions
              console.debug('Error fixing child elements:', error);
            }
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

// Global fix: Ensure all elements have proper tagName property
// This prevents errors from browser extensions that traverse the DOM
(function() {
  'use strict';

  // Fix all existing elements immediately
  function fixAllElements() {
    try {
      const allElements = document.querySelectorAll('*');
      allElements.forEach((el) => {
        fixElementTagName(el);
      });
    } catch (error) {
      // Silently handle errors (e.g., from browser extensions)
      console.debug('Error fixing all elements:', error);
    }
  }

  // Run fix when DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', fixAllElements);
  } else {
    // DOM is already loaded
    fixAllElements();
  }

  // Also fix elements as they're added (handled by MutationObserver in fixTagifyElementsForExtensions)
})();

// Run fix immediately for elements that already exist
if (document.body) {
  fixTagifyElementsForExtensions();
} else {
  // Wait for body to be available
  document.addEventListener('DOMContentLoaded', () => {
    fixTagifyElementsForExtensions();
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

    // Parse existing tags from data attribute or value
    const parseTagsFromValue = () => {
      return existingTagsValue ? existingTagsValue.split(',').map((tag) => tag.trim()).filter((tag) => tag) : [];
    };

    const parseTagsFromData = (data) => {
      const trimmedData = data.trim();
      if (!trimmedData || trimmedData === 'null' || trimmedData === 'undefined') {
        return null;
      }
      try {
        const parsedTags = JSON.parse(trimmedData);
        if (Array.isArray(parsedTags)) {
          return parsedTags.map((tag) => ({
            value: tag.name,
            id: tag.id,
            color: tag.color,
            title: tag.description || tag.name,
            description: tag.description || '',
          }));
        }
      } catch (error) {
        console.warn('Failed to parse existing tags data:', error);
        console.warn('Raw data that failed to parse:', data);
      }
      return null;
    };

    // Try to parse from data attribute first, fallback to value
    const existingTags = existingTagsData ? parseTagsFromData(existingTagsData) : null;
    const finalTags = existingTags || parseTagsFromValue();

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
    fetch('/expenses/tags', {
      credentials: 'include', // Include cookies for authentication (required for CORS)
    })
      .then((response) => {
        // Check if response is JSON before parsing
        const contentType = response.headers.get('content-type');
        if (!contentType || !contentType.includes('application/json')) {
          throw new Error('Invalid response format from server');
        }
        return response.json();
      })
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
          if (finalTags.length > 0 && tagify.value.length === 0) {
            // If we have full tag data (from data-existing-tags), use it directly
            if (finalTags[0] && finalTags[0].id) {
              tagify.addTags(finalTags);
            } else {
              // Fallback: try to match with whitelist
              finalTags.forEach((tagName) => {
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
        // Ensure tagName is fixed for this element
        fixElementTagName(tagEl);
      });
    }, 50);
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
