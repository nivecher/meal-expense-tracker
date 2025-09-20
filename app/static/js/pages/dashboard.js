/**
 * Dashboard Page
 *
 * Handles filter toggle functionality and category dropdown styling for the main dashboard.
 * This replaces the inline JavaScript in the main/index.html template.
 */

document.addEventListener('DOMContentLoaded', () => {
  // Filter toggle functionality
  const filterHeader = document.querySelector('.card-header[data-bs-toggle="collapse"]');
  if (filterHeader) {
    filterHeader.addEventListener('click', function() {
      const icon = this.querySelector('i.fas.fa-chevron-down, i.fas.fa-chevron-up');
      if (icon) {
        icon.classList.toggle('fa-chevron-down');
        icon.classList.toggle('fa-chevron-up');
      }
    });
  }

  // Enhance category dropdown with colors and icons
  const categorySelect = document.getElementById('category');
  if (categorySelect) {
    // Style the options with their colors
    categorySelect.addEventListener('change', function() {
      const selectedOption = this.options[this.selectedIndex];
      if (selectedOption && selectedOption.dataset.color) {
        this.style.backgroundColor = `${selectedOption.dataset.color}20`;
        this.style.borderColor = `${selectedOption.dataset.color}40`;
        this.style.color = selectedOption.dataset.color;
      } else {
        this.style.backgroundColor = '';
        this.style.borderColor = '';
        this.style.color = '';
      }
    });

    // Trigger change event on page load to set initial color
    categorySelect.dispatchEvent(new Event('change'));
  }
});
