/**
 * Tag Badge Styler
 * 
 * Applies custom styling to tag badges based on their data-tag-color attribute.
 * This ensures consistent styling across all pages that display tag badges.
 */
document.addEventListener('DOMContentLoaded', () => {
  // Apply colors to all tag badges on the page
  const tagBadges = document.querySelectorAll('.tag-badge[data-tag-color]');
  tagBadges.forEach((badge) => {
    const color = badge.getAttribute('data-tag-color');
    if (color) {
      // Use setProperty with !important to ensure styles are applied
      badge.style.setProperty('background-color', color, 'important');
      badge.style.setProperty('color', 'white', 'important');
      badge.style.setProperty('border-radius', '20px', 'important');
      badge.style.setProperty('padding', '4px 12px', 'important');
      badge.style.setProperty('font-size', '0.8rem', 'important');
      badge.style.setProperty('font-weight', '500', 'important');
      badge.style.setProperty('box-shadow', '0 2px 4px rgba(0, 0, 0, 0.1)', 'important');
      badge.style.setProperty('transition', 'all 0.2s ease', 'important');
      badge.style.setProperty('border', 'none', 'important');
      badge.style.setProperty('display', 'inline-flex', 'important');
      badge.style.setProperty('align-items', 'center', 'important');
      badge.style.setProperty('margin', '2px', 'important');
      badge.style.setProperty('line-height', '1.2', 'important');
    }
  });
});
