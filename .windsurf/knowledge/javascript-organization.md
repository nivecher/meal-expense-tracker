# JavaScript Code Organization

## Rule: External JavaScript Files

All JavaScript code should be placed in dedicated .js files and included via script tags in HTML templates. No inline
JavaScript or HTML event handlers should be used in HTML files.

### Requirements

1. **File Organization**

- Place all JavaScript in dedicated .js files under `/app/static/js/`
  - Organize by feature/component (e.g., `restaurant-form.js`, `user-preferences.js`)

1. **Event Handling**

- Use `addEventListener()` instead of HTML event attributes (`onclick`, `onsubmit`, etc.)
  - Example:

````

```javascript

// Good
document.getElementById('myButton').addEventListener('click', handleClick);

````

```

// Bad
<button onclick="handleClick()">Click me</button>

```

```

1. **Initialization**

- Use a main initialization function in each JS file
  - Call this function when the DOM is fully loaded
  - Example:

```

```javascript
function initRestaurantForm() {
  // Initialize form handlers
  document.getElementById('restaurantForm').addEventListener('submit', handleFormSubmit);
}
```

```

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', initRestaurantForm);

```

```

1. **Data Attributes**

- Use `data-*` attributes to pass data from HTML to JavaScript
  - Example:

```

```html
<div data-restaurant-id="123" data-is-verified="true">...</div>
```

```javascript
const element = document.querySelector('[data-restaurant-id]');
const restaurantId = element.dataset.restaurantId;
const isVerified = element.dataset.isVerified === 'true';
```

````

1. **HTML Template Example**

   ```html

   <!-- Good -->
   <script src="{{ url_for('static', filename='js/pages/restaurant-form.js') }}"></script>

   <!-- Bad -->
   <script>

````

function handleClick() {
// Inline JavaScript
}

```

   </script>
   <button onclick="handleClick()">Click me</button>

```

### Benefits

- Better separation of concerns
- Improved code maintainability
- Easier testing
- Better caching by browsers
- Cleaner HTML templates

### Related Files

- `/app/static/js/pages/restaurant-form.js` - Example implementation
- `/app/templates/restaurants/form.html` - Example template usage
