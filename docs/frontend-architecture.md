# Frontend Architecture & Design

## Table of Contents

1. [Overview](#overview)
2. [Architecture Principles](#architecture-principles)
3. [Technology Stack](#technology-stack)
4. [Project Structure](#project-structure)
5. [Component Organization](#component-organization)
6. [JavaScript Architecture](#javascript-architecture)
7. [Styling Approach](#styling-approach)
8. [API Integration](#api-integration)
9. [Performance Considerations](#performance-considerations)
10. [Development Workflow](#development-workflow)

## Overview

The Meal Expense Tracker frontend uses a **server-side rendered** approach with **progressive enhancement**.

This architecture follows TIGER principles and prioritizes simplicity, performance, and maintainability over complex client-side frameworks.

### Design Philosophy

- **Server-first**: Primary rendering happens server-side with Jinja2 templates
- **Progressive Enhancement**: JavaScript enhances the user experience but isn't required for core functionality
- **Performance**: Fast initial page loads with minimal JavaScript bundle size
- **Accessibility**: Semantic HTML with ARIA support built-in

## Architecture Principles

### T - Testable

- Modular JavaScript with clear interfaces
- Pure utility functions where possible
- Service layer abstraction for API calls
- Playwright end-to-end testing

### I - Incremental

- Progressive enhancement over baseline HTML/CSS
- Feature-based code organization
- Lazy loading for performance optimization
- Gradual adoption of modern JavaScript features

### G - Goal-oriented

- User experience focused (fast, accessible, intuitive)
- Business feature alignment with backend structure
- Performance metrics tracking
- Mobile-first responsive design

### E - Explicit

- Clear naming conventions for CSS classes and JavaScript modules
- Explicit dependency management through ES6 imports
- Type documentation in JSDoc comments
- Configuration through data attributes

### R - Responsibility-focused

- Separation of concerns: HTML structure, CSS presentation, JavaScript behavior
- Single-purpose JavaScript modules
- Clear separation between page-specific and shared code
- Encapsulated component functionality

## Technology Stack

### Core Technologies

- **Template Engine**: [Jinja2](https://jinja.palletsprojects.com/) (server-side rendering)
- **CSS Framework**: [Bootstrap 5.3.3](https://getbootstrap.com/) for responsive components
- **JavaScript Library**: [jQuery 3.7.1](https://jquery.com/) for DOM manipulation and AJAX
- **Module System**: ES6 modules for code organization
- **Icons**: [Bootstrap Icons](https://icons.getbootstrap.com/) + [Font Awesome](https://fontawesome.com/)

### Enhanced Components

- **Form Controls**: [Select2](https://select2.org/) with Bootstrap 5 theme
- **Charts**: [Chart.js](https://www.chartjs.org/) for data visualization
- **Maps**: [Google Maps JavaScript API](https://developers.google.com/maps/documentation/javascript/)

### Development Tools

- **Linting**: ESLint 9.34.0 with flat config format
- **Formatting**: Prettier 3.2.4 for HTML templates
- **Testing**: Playwright for end-to-end testing
- **Build Process**: Make-based workflow (no webpack/bundling needed)

## Project Structure

```bash
app/
├── static/                          # Static assets
│   ├── css/                        # Stylesheets
│   │   ├── components/             # Component-specific styles
│   │   │   ├── dashboard.css       # Dashboard styling
│   │   │   ├── forms.css          # Form component styles
│   │   │   ├── google-places.css  # Google Maps integration styles
│   │   │   └── navbar.css         # Navigation styling
│   │   ├── main.css               # Global styles and utilities
│   │   └── loading.css            # Loading states and animations
│   │
│   ├── js/                         # JavaScript modules
│   │   ├── components/             # Reusable UI components
│   │   │   ├── avatar-picker.js    # Avatar selection component
│   │   │   └── modern-avatar.js    # Avatar display component
│   │   ├── pages/                  # Page-specific functionality
│   │   │   ├── dashboard.js        # Dashboard interactions
│   │   │   └── restaurant-form.js  # Restaurant form management
│   │   ├── services/               # API and external service integration
│   │   │   └── google-places.js    # Google Places API service
│   │   └── utils/                  # Utility modules
│   │       ├── core-utils.js       # Core utility functions
│   │       ├── google-maps.js      # Google Maps integration
│   │       ├── restaurant-form.js  # Restaurant form utilities
│   │       └── ui-utils.js         # UI helper functions
│   │
│   └── img/                        # Images and icons
│       └── favicons/               # Favicon assets
│
└── templates/                      # Jinja2 templates
    ├── base.html                   # Base template with common head/footer
    ├── base_auth.html              # Authentication-specific base template
    ├── includes/                   # Template partials
    │   ├── navbar.html             # Navigation component
    │   └── breadcrumb.html         # Breadcrumb component
    ├── main/                       # Main application templates
    ├── auth/                       # Authentication templates
    ├── restaurants/                # Restaurant management templates
    ├── expenses/                   # Expense tracking templates
    └── reports/                    # Reporting and analytics templates
```

## Component Organization

### Template Hierarchy

1. **Base Templates**

   - `base.html` - Core layout with navigation, scripts, and global styles
   - `base_auth.html` - Authentication-specific layout for login/register pages
   - Shared meta tags, CDN includes, and global configuration

2. **Template Includes**

   - `includes/navbar.html` - Navigation component with user menu
   - `includes/breadcrumb.html` - Breadcrumb navigation component
   - Reusable template fragments for consistent UI elements

3. **Feature Templates**
   - **Main**: Dashboard, help, about, privacy pages
   - **Auth**: Login, register, profile management
   - **Restaurants**: List, detail, form, import, Google Places search
   - **Expenses**: List, detail, form, import, statistics
   - **Reports**: Analytics dashboard and reporting views

### CSS Architecture

1. **Global Styles** (`main.css`)

   - CSS custom properties for theming
   - Utility classes following Bootstrap conventions
   - Global component overrides

2. **Component Styles** (`css/components/`)

   - **BEM methodology** for naming conventions
   - Scoped styles for specific components
   - Mobile-responsive design patterns

3. **Page Styles**
   - Page-specific styling when needed
   - Loading states and animations
   - Print styles for reports

## JavaScript Architecture

### Module Organization

1. **Page Controllers** (`js/pages/`)

   - Initialize page-specific functionality
   - Coordinate multiple components
   - Handle page-level event delegation

2. **Utility Modules** (`js/utils/`)

   - Pure functions for common operations
   - DOM manipulation helpers
   - Form validation utilities

3. **Service Modules** (`js/services/`)

   - API communication layer
   - External service integration (Google Maps)
   - Data transformation and caching

4. **Component Modules** (`js/components/`)
   - Reusable UI components
   - Self-contained functionality
   - Configuration through data attributes

### State Management

- **Server State**: Primary data source from server-rendered templates
- **Client State**: Minimal client-side state for UI interactions
- **Session State**: HTML5 localStorage for user preferences
- **Form State**: Form validation and auto-save using localStorage
- **Cache State**: Service-level caching for API responses (Google Places, etc.)

## API Integration

### AJAX Patterns

- **Form Submission**: Progressive enhancement with AJAX for better UX
- **Real-time Updates**: Fetch API for dynamic content loading
- **Error Handling**: Consistent error display using Bootstrap toasts
- **Loading States**: Visual feedback during API operations

### CSRF Protection

- **Development**: CSRF tokens automatically included in forms
- **Production (Lambda)**: CSRF disabled for stateless operation
- **API Requests**: CSRF tokens in headers for AJAX calls

## Styling Approach

### CSS Methodology

- **BEM (Block Element Modifier)** for component naming
- **Bootstrap 5 utility classes** for rapid development
- **CSS Custom Properties** for theming and consistency
- **Component-scoped styles** in `css/components/` directory

### Design System

- **Bootstrap 5 Variables**: Custom theme with consistent colors and spacing
- **Icon System**: Bootstrap Icons + Font Awesome for comprehensive coverage
- **Typography**: Bootstrap typography with custom heading styles
- **Color Palette**: Semantic color system (primary, secondary, success, warning, etc.)

### Responsive Design

- **Mobile-first approach** with Bootstrap's grid system
- **Breakpoint strategy**: xs, sm, md, lg, xl following Bootstrap conventions
- **Touch-friendly interfaces** for mobile users
- **Print styles** for expense reports

## Performance Considerations

### Loading Strategy

- **Critical CSS**: Inline critical styles in base templates
- **Progressive Enhancement**: Core functionality works without JavaScript
- **Lazy Loading**: Images and non-critical JavaScript modules
- **CDN Usage**: Bootstrap, jQuery, and Font Awesome from CDN with integrity hashes

### JavaScript Performance

- **ES6 Modules**: Native module system (no bundling required)
- **Event Delegation**: Efficient event handling for dynamic content
- **Debounced Inputs**: Search and autocomplete with proper throttling
- **Minimal Dependencies**: Selective inclusion of third-party libraries

### Caching Strategy

- **Static Assets**: Long-term caching with versioning
- **API Responses**: Service-level caching for Google Places
- **User Preferences**: localStorage for client-side persistence

## Development Workflow

### Code Organization

- **Feature-based structure** aligning with Flask blueprints
- **Shared utilities** for common functionality
- **Page-specific code** in dedicated modules
- **Component isolation** with clear interfaces

### Quality Assurance

- **ESLint Configuration**: Environment-specific rules
- **Pre-commit Hooks**: Automated linting and formatting
- **Prettier Integration**: Consistent HTML template formatting
- **Manual Testing**: Cross-browser and accessibility verification

### Integration with Backend

- **Flask Template Integration**: Seamless data passing from server to client
- **CSRF Integration**: Automatic token handling in development
- **Error Handling**: Consistent error display using Flask flash messages
- **Form Processing**: Progressive enhancement of standard HTML forms

## Best Practices

### JavaScript Guidelines

- **ES6+ Features**: Use modern JavaScript with appropriate browser support
- **Pure Functions**: Favor functional programming patterns
- **Error Handling**: Always handle async operations with try/catch
- **Memory Management**: Proper cleanup of event listeners and timers

### Template Guidelines

- **Semantic HTML**: Use appropriate HTML5 semantic elements
- **Accessibility**: ARIA labels and proper form associations
- **Progressive Enhancement**: Ensure functionality without JavaScript
- **SEO Optimization**: Proper meta tags and structured data

### CSS Guidelines

- **BEM Naming**: `.block__element--modifier` convention
- **Utility-first**: Leverage Bootstrap utilities before custom CSS
- **Component Isolation**: Scoped styles prevent global conflicts
- **Mobile-first**: Design for mobile, enhance for desktop

---
