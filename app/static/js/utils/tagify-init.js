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
  if (tagsInput) {
    // Get existing tags from input value
    const existingTagsValue = tagsInput.value;
    const existingTags = existingTagsValue ? existingTagsValue.split(',').map((tag) => tag.trim()).filter((tag) => tag) : [];

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

          return `
                        <tag title="${tagData.title || tagData.value}"
                             contenteditable='false'
                             spellcheck='false'
                             tabIndex="-1"
                             class="tagify__tag tagify-tag-pretty"
                             data-tagify-tag="true"
                             data-tag-id="${tagId}"
                             style="background-color: ${tagColor}; color: #fff;">
                        <x title='' class='tagify__tag__removeBtn' role='button' aria-label='remove tag'></x>
                        <div>
                            <span class='tagify__tag-text'>${tagData.value}</span>
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
            color: tag.color,
          }));

          // Add existing tags to Tagify after whitelist is loaded
          if (existingTags.length > 0) {
            existingTags.forEach((tagName) => {
              // Find matching tag in whitelist to get ID and color
              const matchingTag = tagify.settings.whitelist.find((tag) => tag.value === tagName);
              const tagData = matchingTag ? {
                value: tagName,
                id: matchingTag.id,
                color: matchingTag.color,
              } : { value: tagName };
              tagify.addTags([tagData]);
            });

            // Apply colors to existing tags after they're added
            setTimeout(() => {
              const tagElements = document.querySelectorAll('.tagify__tag');
              tagElements.forEach((tagEl) => {
                const tagValue = tagEl.querySelector('.tagify__tag-text')?.textContent;
                if (tagValue) {
                  const matchingTag = tagify.settings.whitelist.find((tag) => tag.value === tagValue);
                  if (matchingTag && matchingTag.color) {
                    tagEl.style.setProperty('background-color', matchingTag.color, 'important');
                    tagEl.style.setProperty('color', '#fff', 'important');
                    tagEl.style.setProperty('border', 'none', 'important');
                    tagEl.style.setProperty('box-shadow', '0 2px 4px rgba(0, 0, 0, 0.1)', 'important');
                  }
                }
              });
            }, 100);
          }
        }
      })
      .catch((error) => console.error('Failed to load tags:', error));

    // Force apply colors to all tags
    function applyTagColors() {
      const tagElements = document.querySelectorAll('.tagify__tag');
      tagElements.forEach((tagEl) => {
        const tagValue = tagEl.querySelector('.tagify__tag-text')?.textContent;
        if (tagValue) {
          const matchingTag = tagify.settings.whitelist.find((tag) => tag.value === tagValue);
          if (matchingTag && matchingTag.color) {
            tagEl.style.setProperty('background-color', matchingTag.color, 'important');
            tagEl.style.setProperty('color', '#fff', 'important');
            tagEl.style.setProperty('border', 'none', 'important');
            tagEl.style.setProperty('box-shadow', '0 2px 4px rgba(0, 0, 0, 0.1)', 'important');
          }
        }
      });
    }

    // Apply colors when tags are added
    tagify.on('add', (e) => {
      setTimeout(applyTagColors, 10);
    });

    // Apply colors periodically to catch any missed tags (less frequent now)
    setInterval(applyTagColors, 1000);

    // Make globally available
    window.tagifyInstance = tagify;

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
