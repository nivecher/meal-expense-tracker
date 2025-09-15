/**
 * Profile Page Functionality
 * Handles character counters, avatar picker initialization, and tag manager
 */

export function initProfile() {
    // Character counters
    const textareas = document.querySelectorAll('input[maxlength], textarea[maxlength]');

    textareas.forEach(function(element) {
        const countElement = document.getElementById(element.id + '_count');
        if (countElement) {
            element.addEventListener('input', function() {
                countElement.textContent = element.value.length;
            });
        }
    });

    // Initialize avatar picker with current selection
    if (window.avatarPicker) {
        const currentAvatarUrl = document.getElementById('avatar-url-input').value;
        if (currentAvatarUrl) {
            // Set the current avatar as selected
            setTimeout(() => {
                window.avatarPicker.setSelectedAvatar(currentAvatarUrl);
            }, 100);
        }
    }

    // Initialize tag manager
    initializeTagManager();
}

function initializeTagManager() {
    try {
        // TagManager is already created and initialized globally from tag-manager.js
        // Just check if it exists and is working
        if (window.tagManager && window.tagManager.isInitialized) {
            console.log('TagManager already initialized');
        } else if (window.tagManager) {
            // Initialize if not already done
            window.tagManager.init();
        } else {
            console.warn('TagManager not available globally');
        }
    } catch (error) {
        console.error('Failed to initialize tag manager:', error);
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', initProfile);
