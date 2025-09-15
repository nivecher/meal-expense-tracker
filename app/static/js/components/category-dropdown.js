/**
 * Category Dropdown Component
 * Handles dynamic styling based on selected category color
 */

function init_category_dropdown() {
    const categorySelect = document.querySelector('[data-category-select]');
    if (!categorySelect) return;

    function updateCategoryStyle() {
        const selectedOption = categorySelect.options[categorySelect.selectedIndex];
        if (selectedOption && selectedOption.dataset.color) {
            categorySelect.style.backgroundColor = selectedOption.dataset.color + '20';
            categorySelect.style.borderColor = selectedOption.dataset.color + '40';
            categorySelect.style.color = selectedOption.dataset.color;
        } else {
            categorySelect.style.backgroundColor = '';
            categorySelect.style.borderColor = '';
            categorySelect.style.color = '';
        }
    }

    categorySelect.addEventListener('change', updateCategoryStyle);
    updateCategoryStyle(); // Set initial style
}

// Auto-initialize when DOM is ready
document.addEventListener('DOMContentLoaded', init_category_dropdown);

// Export for manual initialization if needed
export { init_category_dropdown };
