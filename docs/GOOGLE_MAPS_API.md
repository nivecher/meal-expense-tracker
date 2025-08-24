# Google Maps API Integration Guide

## Overview

This document outlines our approach to Google Maps API integration, which uses smart API detection to automatically use modern APIs when available while maintaining backward compatibility with legacy APIs.

## Architecture

### Smart API Detection

Our `googlePlacesService` automatically detects which Google Maps APIs are available and uses the most modern ones:

```javascript
// Automatically detects and uses modern APIs when available
if (this.useModernAPI) {
  // Use modern Place.searchByText()
  const { places } = await google.maps.places.Place.searchByText(searchRequest);
} else {
  // Fallback to legacy PlacesService
  this.placesService.nearbySearch(request, callback);
}
```

### API Compatibility Matrix

| Feature       | Modern API                                              | Legacy API                                  | Status            |
| ------------- | ------------------------------------------------------- | ------------------------------------------- | ----------------- |
| Place Search  | `Place.searchByText()`                                  | `PlacesService.nearbySearch()`              | ✅ Both Supported |
| Place Details | `Place.fetchFields()`                                   | `PlacesService.getDetails()`                | ✅ Both Supported |
| Autocomplete  | `PlaceAutocompleteElement`                              | `Autocomplete`                              | ✅ Both Supported |
| Predictions   | `AutocompleteSuggestion.fetchAutocompleteSuggestions()` | `AutocompleteService.getPlacePredictions()` | ✅ Both Supported |

## Usage Guidelines

### 1. Always Use the Service Layer

**✅ Correct:**

```javascript
import { googlePlacesService } from '../services/google-places.js';

// Search for places
const results = await googlePlacesService.searchNearby('pizza', location);

// Get place details
const details = await googlePlacesService.getPlaceDetails(placeId);

// Create autocomplete
const autocomplete = googlePlacesService.createAutocomplete(inputElement);
```

**❌ Incorrect:**

```javascript
// Don't use APIs directly
const placesService = new google.maps.places.PlacesService(map);
const autocomplete = new google.maps.places.Autocomplete(inputElement);
```

### 2. Service Initialization

```javascript
// Initialize the service (handles API detection automatically)
await googlePlacesService.init();

// Check which APIs are being used
if (googlePlacesService.useModernAPI) {
  console.log('Using modern Google Maps APIs');
} else {
  console.log('Using legacy Google Maps APIs');
}
```

### 3. Error Handling

```javascript
try {
  const results = await googlePlacesService.searchNearby(query, location);
  // Process results
} catch (error) {
  if (error.message.includes('APIs not available')) {
    // Handle API availability issues
    console.warn('Some Google Maps APIs not available');
  } else {
    // Handle other errors
    console.error('Search failed:', error);
  }
}
```

## Migration Strategy

### Phase 1: Service Layer Implementation ✅ COMPLETED

- [x] Created `googlePlacesService` with smart API detection
- [x] Implemented modern API methods (`Place.searchByText`, `Place.fetchFields`)
- [x] Implemented legacy API fallbacks (`PlacesService`, `AutocompleteService`)
- [x] Added automatic API availability detection

### Phase 2: Application Integration ✅ COMPLETED

- [x] Updated `restaurant-form.js` to use service
- [x] Updated `restaurant-search-init.js` to use service
- [x] Updated `google-places.js` service implementation
- [x] Maintained backward compatibility

### Phase 3: Testing & Validation 🔄 IN PROGRESS

- [ ] Test modern API functionality
- [ ] Test legacy API fallbacks
- [ ] Validate no deprecation warnings
- [ ] Performance testing

## Best Practices

### 1. API Version Management

- **Never hardcode API versions** - let the service detect automatically
- **Test with both modern and legacy APIs** to ensure compatibility
- **Monitor deprecation warnings** and update as needed

### 2. Error Handling

- **Always handle API availability errors** gracefully
- **Provide user-friendly fallbacks** when APIs are unavailable
- **Log API detection results** for debugging

### 3. Performance

- **Modern APIs are generally faster** - prefer them when available
- **Legacy APIs are reliable fallbacks** - maintain them for compatibility
- **Cache API detection results** to avoid repeated checks

## Troubleshooting

### Common Issues

#### 1. "APIs not available" Error

```javascript
// Check if service is properly initialized
if (!googlePlacesService.initialized) {
  await googlePlacesService.init();
}

// Check which APIs are available
console.log('Modern APIs:', googlePlacesService.useModernAPI);
```

#### 2. Deprecation Warnings

- Ensure you're using `googlePlacesService` instead of direct API calls
- Check that the service is properly detecting modern APIs
- Verify Google Maps API is loaded with correct libraries

#### 3. Autocomplete Not Working

```javascript
// Check autocomplete type
const autocomplete = googlePlacesService.createAutocomplete(inputElement);
console.log('Autocomplete type:', autocomplete.constructor.name);

// Handle events appropriately
if (autocomplete.addEventListener) {
  // Modern PlaceAutocompleteElement
  autocomplete.addEventListener('gmp-placeselect', handler);
} else {
  // Legacy Autocomplete
  autocomplete.addListener('place_changed', handler);
}
```

## Future Considerations

### API Evolution

- **Google continues to evolve** their Maps JavaScript API
- **New APIs may become available** - our service will detect them automatically
- **Legacy APIs will eventually be deprecated** - we're prepared for this transition

### Performance Improvements

- **Modern APIs offer better performance** and features
- **Consider migrating fully to modern APIs** once they're stable and widely available
- **Monitor Google's deprecation timeline** for legacy APIs

### Alternative Services

- **Consider other mapping services** if Google's APIs become problematic
- **Our service layer abstraction** makes it easy to switch providers
- **Maintain vendor independence** through consistent interfaces

## Conclusion

Our smart API detection approach provides the best of both worlds:

- **Modern APIs** when available for enhanced performance and features
- **Legacy APIs** as reliable fallbacks for compatibility
- **Seamless user experience** regardless of API availability
- **Future-proof architecture** that adapts to Google's API evolution

By using the `googlePlacesService` consistently throughout the application, we ensure:

- ✅ No deprecation warnings
- ✅ Optimal performance with modern APIs
- ✅ Reliable fallbacks with legacy APIs
- ✅ Easy maintenance and updates
- ✅ Consistent error handling and logging
