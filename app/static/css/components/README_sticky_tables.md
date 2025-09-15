# Sticky Table Headers & Frozen Columns

This document describes the implementation of sticky table headers and frozen columns in the Meal Expense Tracker application.

## Overview

Three different CSS classes are available to enhance table usability:

1. **`.table-sticky-header`** - Headers remain visible during vertical scrolling
2. **`.table-frozen-columns`** - First column stays fixed during horizontal scrolling
3. **`.table-sticky-frozen`** - Combines both sticky headers and frozen first column

## Features

### 🎯 Core Functionality

- **Sticky Headers**: Table headers remain visible when scrolling through long data sets
- **Frozen Columns**: First column stays fixed when horizontally scrolling wide tables
- **Combined Mode**: Both features work together seamlessly

### 📱 Responsive Design

- Mobile-optimized with reduced padding and adjusted heights
- Custom scrollbars for better visual experience
- Touch-friendly scrolling on mobile devices

### ⚡ Performance

- Hardware-accelerated scrolling using CSS transforms
- Debounced scroll events for smooth performance
- Passive event listeners to prevent scroll jank
- Efficient z-index management

### 🎨 Visual Enhancements

- Dynamic shadow effects that intensify with scroll distance
- Smooth transitions and hover effects
- Proper visual hierarchy with layered elements

## Usage

### Basic Implementation

Replace standard `table-responsive` divs with one of the sticky classes:

```html
<!-- Before: Standard responsive table -->
<div class="table-responsive">
  <table class="table table-hover">
    <!-- table content -->
  </table>
</div>

<!-- After: Sticky headers -->
<div class="table-sticky-header">
  <table class="table table-hover">
    <!-- table content -->
  </table>
</div>
```

### Available Classes

#### 1. Sticky Headers Only

Best for tables with many rows but standard width:

```html
<div class="table-sticky-header">
  <table class="table table-hover">
    <thead>
      <tr>
        <th>Date</th>
        <th>Restaurant</th>
        <th>Amount</th>
      </tr>
    </thead>
    <tbody>
      <!-- many rows of data -->
    </tbody>
  </table>
</div>
```

#### 2. Frozen First Column

Best for wide tables where first column provides important context:

```html
<div class="table-frozen-columns">
  <table class="table table-hover">
    <thead>
      <tr>
        <th style="min-width: 150px;">Restaurant Name</th>
        <th style="min-width: 120px;">Location</th>
        <th style="min-width: 100px;">Cuisine</th>
        <!-- many more columns -->
      </tr>
    </thead>
    <tbody>
      <!-- table rows -->
    </tbody>
  </table>
</div>
```

#### 3. Combined Sticky & Frozen

Best for large data tables with many rows and columns:

```html
<div class="table-sticky-frozen">
  <table class="table table-hover">
    <thead>
      <tr>
        <th style="min-width: 150px;">Primary Column</th>
        <th style="min-width: 120px;">Data Column 1</th>
        <!-- many more columns -->
      </tr>
    </thead>
    <tbody>
      <!-- many rows of data -->
    </tbody>
  </table>
</div>
```

### JavaScript Enhancement

The JavaScript component (`sticky-tables.js`) provides additional functionality:

```javascript
// Auto-initialize all sticky tables
StickyTable.init();

// Initialize specific table
const container = document.querySelector(".my-table");
StickyTable.initTable(container);

// Dynamically add sticky functionality
StickyTable.addStickyClasses(tableContainer, "both");
```

## Implementation Details

### CSS Architecture

The implementation uses modern CSS features:

- `position: sticky` for headers and columns
- Proper z-index layering (headers: 10, frozen: 5, combined: 15)
- Custom scrollbar styling
- Responsive breakpoints for mobile optimization

### JavaScript Features

- **Automatic Initialization**: Tables are enhanced on page load
- **Dynamic Content Support**: Works with AJAX-loaded content (htmx compatible)
- **Performance Optimization**: Debounced scroll events and passive listeners
- **Shadow Effects**: Dynamic shadow intensity based on scroll position
- **Resize Handling**: Recalculates dimensions on window resize

### Browser Support

- **Modern Browsers**: Full support (Chrome 56+, Firefox 59+, Safari 13+, Edge 16+)
- **Position Sticky**: Uses native CSS sticky positioning
- **Fallback**: Graceful degradation to standard responsive tables

## Best Practices

### When to Use Each Type

1. **Sticky Headers** (`table-sticky-header`)

   - Tables with 20+ rows
   - Standard width tables (≤10 columns)
   - When vertical scrolling is primary concern

2. **Frozen Columns** (`table-frozen-columns`)

   - Wide tables (10+ columns)
   - When first column is critical for context (names, IDs, dates)
   - Primarily horizontal scrolling needed

3. **Combined** (`table-sticky-frozen`)
   - Large datasets (20+ rows, 8+ columns)
   - Complex data tables requiring both scroll directions
   - Dashboard-style data presentation

### Performance Considerations

- Limit table height with `max-height` (default: 70vh desktop, 60vh mobile)
- Use `min-width` on columns to ensure proper layout
- Consider pagination for very large datasets (>1000 rows)
- Test on various screen sizes and devices

### Accessibility

- Maintains keyboard navigation
- Screen reader compatible
- Focus management preserved
- High contrast mode support

## Examples in Application

Current implementations:

- **Main Expenses Table**: Uses `table-sticky-header` for expense list
- **Restaurant List**: Uses `table-sticky-frozen` for wide restaurant data
- **Search Results**: Uses `table-sticky-header` for search results

## Troubleshooting

### Common Issues

1. **Headers not sticking**: Ensure container has proper height constraint
2. **Frozen column overlapping**: Check z-index values and background colors
3. **Performance issues**: Reduce table size or implement pagination
4. **Mobile layout problems**: Test responsive breakpoints

### Debugging

Enable development mode to see additional console logging:

```javascript
// Add to page for debugging
window.STICKY_TABLE_DEBUG = true;
```

## Future Enhancements

Potential improvements:

- Multiple frozen columns support
- Virtual scrolling for very large datasets
- Column resizing capabilities
- Export functionality with sticky headers
- Keyboard shortcuts for navigation
